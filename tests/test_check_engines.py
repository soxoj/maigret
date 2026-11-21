"""Offline coverage for engine detection and safe database updates."""

import asyncio
import json
import logging
from unittest.mock import AsyncMock, Mock

import pytest

from maigret import checking
from maigret.errors import CheckError
from maigret.result import MaigretCheckResult, MaigretCheckStatus
from maigret.sites import MaigretDatabase, MaigretEngine, MaigretSite
from utils import check_engines

MARKERS = ["engine-fingerprint-one", "engine-fingerprint-two"]
MATCHING_HTML = "<html>engine-fingerprint-one engine-fingerprint-two</html>"
LOGGER = logging.getLogger(__name__)


def _engine_data(markers=None):
    return {
        "presenseStrs": MARKERS if markers is None else markers,
        "site": {
            "url": "{urlMain}/users/{username}",
            "checkType": "message",
            "presenseStrs": ["profile exists"],
            "absenceStrs": ["profile missing"],
            "usernameClaimed": "known",
            "usernameUnclaimed": "noonewouldeverusethis7",
        },
    }


@pytest.fixture
def site():
    return MaigretSite(
        "Example",
        {
            "urlMain": "https://example.invalid",
            "url": "https://example.invalid/users/{username}",
            "headers": {"X-Test": "offline"},
            "encoding": "utf-8",
        },
    )


@pytest.fixture
def engine():
    return MaigretEngine("DisplayNameNotPresentInHTML", _engine_data())


def _install_checker(monkeypatch, responses):
    """Fake only the HTTP boundary, retaining real site/database models."""
    instances = []

    class OfflineChecker:
        def __init__(self, **kwargs):
            self.url = None
            self.close = AsyncMock()
            instances.append(self)

        def prepare(self, **kwargs):
            self.url = kwargs["url"]

        async def check(self):
            return responses[self.url]

    monkeypatch.setattr(check_engines, "SimpleAiohttpChecker", OfflineChecker)
    return instances


@pytest.mark.asyncio
async def test_detection_uses_all_markers_and_current_response_tuple(
    monkeypatch, site, engine
):
    checker = Mock()
    checker.check = AsyncMock(return_value=(MATCHING_HTML, 200, None))
    checker.close = AsyncMock()
    monkeypatch.setattr(
        check_engines, "SimpleAiohttpChecker", Mock(return_value=checker)
    )

    result = await check_engines.check_engine_of_site(
        site, engine, asyncio.Semaphore(1), LOGGER
    )

    assert result == site.name
    checker.prepare.assert_called_once_with(
        url=site.url_main,
        headers=site.headers,
        allow_redirects=True,
        timeout=10,
        encoding=site.encoding,
    )
    checker.close.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "html,error",
    [
        ("engine-fingerprint-one", None),
        ("DisplayNameNotPresentInHTML", None),
        ("", None),
        (MATCHING_HTML, CheckError("Request timeout")),
    ],
)
async def test_partial_markers_or_transport_error_do_not_match(
    monkeypatch, site, engine, html, error
):
    instances = _install_checker(monkeypatch, {site.url_main: (html, 200, error)})

    result = await check_engines.check_engine_of_site(
        site, engine, asyncio.Semaphore(1), LOGGER
    )

    assert result is None
    instances[0].close.assert_awaited_once()


def test_database_updates_preserve_multiple_entries_and_metadata(tmp_path):
    prefix, accepted, suffix = _database_source()
    original = prefix + accepted + suffix
    filename = tmp_path / "data.json"
    filename.write_bytes(original.encode("utf-8"))
    updates = {
        "Rejected": {"engine": "A much longer engine name", "tags": ["日本語"]},
        "Accepted": {"engine": "DetectMe"},
    }

    check_engines._save_site_updates(filename, original, updates)

    saved = filename.read_bytes().decode("utf-8")
    parsed = json.loads(saved)
    assert parsed["sites"]["Rejected"] == updates["Rejected"]
    assert parsed["sites"]["Accepted"] == updates["Accepted"]
    assert saved.endswith(suffix)
    assert parsed["metadata"] == json.loads(original)["metadata"]


def test_database_changed_during_checks_is_not_overwritten(tmp_path):
    prefix, accepted, suffix = _database_source()
    original = prefix + accepted + suffix
    filename = tmp_path / "data.json"
    newer = original.replace("https://accepted.invalid", "https://edited.invalid")
    filename.write_bytes(newer.encode("utf-8"))

    with pytest.raises(ValueError, match="database changed"):
        check_engines._save_site_updates(
            filename, original, {"Accepted": {"engine": "DetectMe"}}
        )

    assert filename.read_bytes() == newer.encode("utf-8")


@pytest.mark.asyncio
async def test_empty_marker_list_cannot_match_every_site(monkeypatch, site):
    engine = MaigretEngine("Undetectable", _engine_data([]))
    instances = _install_checker(
        monkeypatch, {site.url_main: (MATCHING_HTML, 200, None)}
    )

    result = await check_engines.check_engine_of_site(
        site, engine, asyncio.Semaphore(1), LOGGER
    )

    assert result is None
    for checker in instances:
        checker.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancellation_closes_checker_and_releases_semaphore(
    monkeypatch, site, engine
):
    checker = Mock()
    checker.check = AsyncMock(side_effect=asyncio.CancelledError)
    checker.close = AsyncMock()
    monkeypatch.setattr(
        check_engines, "SimpleAiohttpChecker", Mock(return_value=checker)
    )
    semaphore = asyncio.Semaphore(1)

    with pytest.raises(asyncio.CancelledError):
        await check_engines.check_engine_of_site(site, engine, semaphore, LOGGER)

    checker.close.assert_awaited_once()
    assert not semaphore.locked()


@pytest.mark.asyncio
async def test_semaphore_limits_concurrent_requests(monkeypatch, site, engine):
    started = asyncio.Event()
    release = asyncio.Event()
    active = 0
    highest_active = 0
    instances = []

    class GatedChecker:
        def __init__(self, **kwargs):
            self.close = AsyncMock()
            instances.append(self)

        def prepare(self, **kwargs):
            pass

        async def check(self):
            nonlocal active, highest_active
            active += 1
            highest_active = max(highest_active, active)
            started.set()
            try:
                await release.wait()
                return MATCHING_HTML, 200, None
            finally:
                active -= 1

    monkeypatch.setattr(check_engines, "SimpleAiohttpChecker", GatedChecker)
    semaphore = asyncio.Semaphore(1)
    tasks = [
        asyncio.create_task(
            check_engines.check_engine_of_site(site, engine, semaphore, LOGGER)
        )
        for _ in range(2)
    ]
    try:
        await asyncio.wait_for(started.wait(), timeout=1)
        await asyncio.sleep(0)
        assert highest_active == 1
    finally:
        release.set()
        results = await asyncio.gather(*tasks)

    assert results == [site.name, site.name]
    assert highest_active == 1
    for checker in instances:
        checker.close.assert_awaited_once()


def _database_source():
    """Keep unusual formatting around the one entry allowed to change."""
    prefix = (
        '{\r\n  "sites" : {\r\n'
        '    "Rejected" : { "urlMain" : "https://rejected.invalid", '
        '"url" : "https://rejected.invalid/{username}", "tags" : ["unchecked"] },\r\n'
        '    "Accepted" : '
    )
    accepted = (
        '{ "urlMain" : "https://accepted.invalid", '
        '"url" : "https://accepted.invalid/users/{username}", '
        '"usernameClaimed" : "known", '
        '"usernameUnclaimed" : "noonewouldeverusethis7" }'
    )
    suffix = (
        ',\r\n    "Disabled" : { "disabled" : true, '
        '"urlMain" : "https://disabled.invalid", '
        '"url" : "https://disabled.invalid/{username}" },\r\n'
        '    "Assigned" : { "engine" : "Other", '
        '"urlMain" : "https://assigned.invalid", '
        '"url" : "https://assigned.invalid/{username}" }\r\n  },\r\n'
        '  "engines" : '
        + json.dumps({"DetectMe": _engine_data(), "Other": _engine_data(["other"])})
        + ',\r\n  "tags" : ["unchecked"],\r\n'
        '  "metadata" : { "escaped" : "A \\\"quote\\\" and } brace", '
        '"Accepted" : { "keep" : true } }\r\n}\r\n'
    )
    return prefix, accepted, suffix


@pytest.mark.asyncio
async def test_only_validated_sites_are_saved_without_touching_other_bytes(
    monkeypatch, tmp_path
):
    prefix, accepted, suffix = _database_source()
    filename = tmp_path / "data.json"
    filename.write_bytes((prefix + accepted + suffix).encode("utf-8"))
    instances = _install_checker(
        monkeypatch,
        {
            "https://rejected.invalid": (MATCHING_HTML, 200, None),
            "https://accepted.invalid": (MATCHING_HTML, 200, None),
        },
    )

    async def validate_candidate(site, logger, semaphore, db, **kwargs):
        candidate = site
        assert candidate.engine == "DetectMe"
        if candidate.name == "Rejected":
            # Self-checks can mutate their database even when validation fails.
            candidate.disabled = True
            candidate.tags.append("failed-validation")
            db.update_site(candidate)
            return {
                "disabled": False,
                "issues": ["Claimed username is missing"],
                "recommendations": ["Diagnostic, not site configuration"],
            }
        return {
            "disabled": False,
            "issues": [],
            "recommendations": ["Diagnostic, not site configuration"],
        }

    validation = AsyncMock(side_effect=validate_candidate)
    monkeypatch.setattr(check_engines, "site_self_check", validation)

    updated = await check_engines.check_engines(
        str(filename), engine_name="DetectMe", no_progressbar=True, max_connections=1
    )

    saved = filename.read_bytes().decode("utf-8")
    parsed = json.loads(saved)
    assert updated == 1
    assert saved.startswith(prefix)
    assert saved.endswith(suffix)
    assert "engine" not in parsed["sites"]["Rejected"]
    assert parsed["sites"]["Accepted"]["engine"] == "DetectMe"
    assert "issues" not in parsed["sites"]["Accepted"]
    assert "recommendations" not in parsed["sites"]["Accepted"]
    assert validation.await_count == 2
    assert {checker.url for checker in instances} == {
        "https://rejected.invalid",
        "https://accepted.invalid",
    }
    for checker in instances:
        checker.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_no_matches_leave_database_byte_identical(monkeypatch, tmp_path):
    prefix, accepted, suffix = _database_source()
    original = (prefix + accepted + suffix).encode("utf-8")
    filename = tmp_path / "data.json"
    filename.write_bytes(original)
    _install_checker(
        monkeypatch,
        {
            "https://rejected.invalid": ("engine-fingerprint-one", 200, None),
            "https://accepted.invalid": ("unrelated HTML", 200, None),
        },
    )
    validation = AsyncMock()
    monkeypatch.setattr(check_engines, "site_self_check", validation)

    updated = await check_engines.check_engines(
        str(filename), engine_name="DetectMe", no_progressbar=True
    )

    assert updated == 0
    assert filename.read_bytes() == original
    validation.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "unclaimed_status",
    [MaigretCheckStatus.AVAILABLE, MaigretCheckStatus.CLAIMED],
)
async def test_real_self_check_requires_a_valid_claimed_and_unclaimed_pair(
    monkeypatch, tmp_path, unclaimed_status
):
    """Exercise the real self-check API while replacing its network search."""
    filename = tmp_path / "data.json"
    original = json.dumps(
        {
            "sites": {
                "Candidate": {
                    "urlMain": "https://candidate.invalid",
                    "url": "https://candidate.invalid/users/{username}",
                    "usernameClaimed": "known",
                    "usernameUnclaimed": "noonewouldeverusethis7",
                    "tags": ["unchecked"],
                }
            },
            "engines": {"DetectMe": _engine_data()},
            "tags": ["unchecked"],
        },
        indent=2,
    ).encode("utf-8")
    filename.write_bytes(original)
    instances = _install_checker(
        monkeypatch, {"https://candidate.invalid": (MATCHING_HTML, 200, None)}
    )

    async def offline_search(*, username, site_dict, **kwargs):
        candidate = site_dict["Candidate"]
        assert candidate.engine == "DetectMe"
        status = MaigretCheckStatus.CLAIMED if username == "known" else unclaimed_status
        return {
            candidate.name: {
                "status": MaigretCheckResult(
                    username,
                    candidate.name,
                    candidate.url.replace("{username}", username),
                    status,
                ),
                "http_status": 200 if username == "known" else 404,
            }
        }

    search = AsyncMock(side_effect=offline_search)
    monkeypatch.setattr(checking, "maigret", search)

    updated = await check_engines.check_engines(
        str(filename), engine_name="DetectMe", no_progressbar=True
    )

    assert [call.kwargs["username"] for call in search.await_args_list] == [
        "known",
        "noonewouldeverusethis7",
    ]
    saved = json.loads(filename.read_bytes())
    saved_site = saved["sites"]["Candidate"]
    assert "issues" not in saved_site
    assert "recommendations" not in saved_site
    if unclaimed_status == MaigretCheckStatus.AVAILABLE:
        assert updated == 1
        assert saved_site["engine"] == "DetectMe"
        assert "unchecked" not in saved_site.get("tags", [])
    else:
        assert updated == 0
        assert "engine" not in saved_site
        assert filename.read_bytes() == original
    instances[0].close.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,attribute,explicit_value,engine_default",
    [
        ("ignore403", "ignore403", False, True),
        ("urlProbe", "url_probe", "", "{urlMain}/api/users/{username}"),
        ("encoding", "encoding", None, "utf-8"),
    ],
)
async def test_validated_overrides_and_raw_metadata_survive_database_reload(
    monkeypatch, tmp_path, field, attribute, explicit_value, engine_default
):
    """The saved configuration must retain the settings that passed validation."""
    original_site = {
        "urlMain": "https://candidate.invalid",
        "url": "https://candidate.invalid/users/{username}",
        "usernameClaimed": "known",
        "usernameUnclaimed": "noonewouldeverusethis7",
        "tags": ["unchecked", "sample"],
        "headers": {},
        "customMetadata": {
            "enabled": False,
            "empty": "",
            "items": [],
            "settings": {},
            "nullable": None,
        },
        field: explicit_value,
    }
    engine_data = _engine_data()
    engine_data["site"][field] = engine_default
    filename = tmp_path / "data.json"
    filename.write_text(
        json.dumps(
            {
                "sites": {"Candidate": original_site},
                "engines": {"DetectMe": engine_data},
                "tags": ["unchecked", "sample"],
            }
        ),
        encoding="utf-8",
    )
    instances = _install_checker(
        monkeypatch, {"https://candidate.invalid": (MATCHING_HTML, 200, None)}
    )
    validated_values = []

    async def offline_search(*, username, site_dict, **kwargs):
        candidate = site_dict["Candidate"]
        assert candidate.engine == "DetectMe"
        value = getattr(candidate, attribute)
        assert value == explicit_value
        validated_values.append(value)
        status = (
            MaigretCheckStatus.CLAIMED
            if username == "known"
            else MaigretCheckStatus.AVAILABLE
        )
        return {
            candidate.name: {
                "status": MaigretCheckResult(
                    username,
                    candidate.name,
                    candidate.url.replace("{username}", username),
                    status,
                ),
                "http_status": 200 if username == "known" else 404,
            }
        }

    search = AsyncMock(side_effect=offline_search)
    monkeypatch.setattr(checking, "maigret", search)

    updated = await check_engines.check_engines(
        str(filename), engine_name="DetectMe", no_progressbar=True
    )

    assert updated == 1
    assert search.await_count == 2
    assert validated_values == [explicit_value, explicit_value]
    saved = json.loads(filename.read_bytes())
    expected_site = dict(original_site, engine="DetectMe", tags=["sample"])
    assert saved["sites"]["Candidate"] == expected_site
    reloaded = MaigretDatabase().load_from_json(saved).sites[0]
    assert getattr(reloaded, attribute) == validated_values[0]
    instances[0].close.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancelling_engine_scan_closes_all_detection_children(
    monkeypatch, tmp_path
):
    started = asyncio.Event()
    release = asyncio.Event()
    instances = []
    children = set()

    class GatedChecker:
        def __init__(self, **kwargs):
            self.close = AsyncMock()
            instances.append(self)

        def prepare(self, **kwargs):
            pass

        async def check(self):
            children.add(asyncio.current_task())
            if len(children) == 2:
                started.set()
            await release.wait()
            return MATCHING_HTML, 200, None

    monkeypatch.setattr(check_engines, "SimpleAiohttpChecker", GatedChecker)
    validation = AsyncMock()
    monkeypatch.setattr(check_engines, "site_self_check", validation)
    filename = tmp_path / "data.json"
    original = json.dumps(
        {
            "sites": {
                name: {
                    "urlMain": f"https://{name.lower()}.invalid",
                    "url": f"https://{name.lower()}.invalid/users/{{username}}",
                }
                for name in ["First", "Second"]
            },
            "engines": {"DetectMe": _engine_data()},
        }
    ).encode("utf-8")
    filename.write_bytes(original)
    scan = asyncio.create_task(
        check_engines.check_engines(
            str(filename), no_progressbar=True, max_connections=2
        )
    )
    try:
        await asyncio.wait_for(started.wait(), timeout=1)
        scan.cancel()
        with pytest.raises(asyncio.CancelledError):
            await scan

        assert len(children) == 2
        assert all(child.done() for child in children)
        for checker in instances:
            checker.close.assert_awaited_once()
        validation.assert_not_awaited()
        assert filename.read_bytes() == original
    finally:
        # Clean up even when the regression leaves children running.
        scan.cancel()
        for child in children:
            child.cancel()
        release.set()
        await asyncio.gather(scan, *children, return_exceptions=True)
