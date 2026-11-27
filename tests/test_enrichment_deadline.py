"""Optional enrichment must not erase an established primary result at timeout."""

import asyncio
import logging
from unittest.mock import Mock

import pytest

from maigret import checking
from maigret.result import MaigretCheckStatus
from maigret.sites import MaigretSite


@pytest.fixture
def enrichment_scan(monkeypatch):
    calls = []
    cancelled = asyncio.Event()
    entered = asyncio.Event()
    behavior = {"primary": "claimed", "secondary": "hang"}
    site = MaigretSite(
        "Local",
        {
            "urlMain": "https://example.test",
            "url": "https://example.test/{username}",
            "checkType": "status_code",
        },
    )

    class Checker(checking.CheckerBase):
        def prepare(self, **kwargs):
            self.__dict__.update(kwargs)

        async def check(self):
            assert self.url is not None
            calls.append(self.url)
            kind = "secondary" if "/extra" in self.url else "primary"
            action = "claimed" if self.url.endswith("/extra/done") else behavior[kind]
            if action == "hang":
                entered.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.set()
            if action == "missing":
                return "not found", 404, None
            return "profile", 200, None

    monkeypatch.setattr(checking, "SimpleAiohttpChecker", Checker)
    monkeypatch.setattr(
        checking,
        "mutate_url",
        lambda url: [("https://example.test/extra", {})],
    )
    monkeypatch.setattr(
        checking, "extract_ids_data", lambda *args: {"bio": "secondary data"}
    )
    notify = Mock()

    async def scan(**kwargs):
        return await checking.maigret(
            "local-demo",
            {site.name: site},
            logging.getLogger(__name__),
            query_notify=notify,
            timeout=0.01,
            no_progressbar=True,
            is_enrich_enabled=kwargs.pop("enrich", True),
            **kwargs,
        )

    return scan, behavior, calls, notify, entered, cancelled


@pytest.mark.asyncio
async def test_enrichment_deadline_preserves_claimed_result(enrichment_scan):
    scan, _, calls, notify, _, cancelled = enrichment_scan
    result = (await scan())["Local"]
    await asyncio.wait_for(cancelled.wait(), timeout=1)
    assert result["status"].status == MaigretCheckStatus.CLAIMED
    assert result["status"].error is None
    assert result["url_user"] == "https://example.test/local-demo"
    assert result["http_status"] == 200
    assert len(calls) == 2
    notify.update.assert_called_once_with(result["status"], False)
    notify.finish.assert_called_once()


@pytest.mark.asyncio
async def test_enrichment_deadline_does_not_retry_primary(enrichment_scan):
    scan, _, calls, _, _, cancelled = enrichment_scan
    result = (await scan(retries=2))["Local"]
    await asyncio.wait_for(cancelled.wait(), timeout=1)
    assert result["status"].status == MaigretCheckStatus.CLAIMED
    assert calls.count("https://example.test/local-demo") == 1


@pytest.mark.asyncio
async def test_primary_deadline_remains_unknown(enrichment_scan):
    scan, behavior, calls, notify, _, cancelled = enrichment_scan
    behavior["primary"] = "hang"
    result = (await scan())["Local"]
    await asyncio.wait_for(cancelled.wait(), timeout=1)
    assert result["status"].status == MaigretCheckStatus.UNKNOWN
    assert result["status"].error.type == "Request failed"
    assert calls == ["https://example.test/local-demo"]
    notify.update.assert_not_called()


@pytest.mark.asyncio
async def test_completed_enrichment_notifies_with_extra_data(enrichment_scan):
    scan, behavior, calls, notify, _, _ = enrichment_scan
    behavior["secondary"] = "claimed"
    observed = []
    notify.update.side_effect = lambda status, similar: observed.append(
        dict(status.ids_data)
    )
    result = (await scan())["Local"]
    assert result["status"].status == MaigretCheckStatus.CLAIMED
    assert result["status"].ids_data["bio"] == "secondary data"
    assert observed == [{"bio": "secondary data"}]
    assert len(calls) == 2
    notify.update.assert_called_once()


@pytest.mark.asyncio
async def test_missing_profile_is_not_enriched(enrichment_scan):
    scan, behavior, calls, notify, _, _ = enrichment_scan
    behavior["primary"] = "missing"
    result = (await scan())["Local"]
    assert result["status"].status == MaigretCheckStatus.AVAILABLE
    assert calls == ["https://example.test/local-demo"]
    notify.update.assert_called_once_with(result["status"], False)


@pytest.mark.asyncio
async def test_disabled_enrichment_is_unchanged(enrichment_scan):
    scan, _, calls, notify, _, _ = enrichment_scan
    result = (await scan(enrich=False))["Local"]
    assert result["status"].status == MaigretCheckStatus.CLAIMED
    assert calls == ["https://example.test/local-demo"]
    notify.update.assert_called_once_with(result["status"], False)


@pytest.mark.asyncio
async def test_stop_during_enrichment_still_cancels_scan(enrichment_scan):
    scan, _, _, _, entered, cancelled = enrichment_scan
    task = asyncio.create_task(scan())
    await asyncio.wait_for(entered.wait(), timeout=1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.wait_for(cancelled.wait(), timeout=1)


@pytest.mark.asyncio
async def test_deadline_keeps_completed_secondary_fields(enrichment_scan, monkeypatch):
    scan, _, calls, _, _, cancelled = enrichment_scan
    monkeypatch.setattr(
        checking,
        'mutate_url',
        lambda url: [
            ('https://example.test/extra/done', {}),
            ('https://example.test/extra/hang', {}),
        ],
    )
    monkeypatch.setattr(
        checking,
        'extract_ids_data',
        lambda *args: {
            'bio': 'secondary data',
            'website': 'https://example.test/linked',
        },
    )
    result = (await scan())['Local']
    await asyncio.wait_for(cancelled.wait(), timeout=1)
    assert result['status'].status == MaigretCheckStatus.CLAIMED
    assert result['status'].ids_data['bio'] == 'secondary data'
    assert 'https://example.test/linked' in result['ids_links']
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_slow_cancellation_cleanup_does_not_extend_deadline(
    enrichment_scan, monkeypatch
):
    scan, _, _, notify, entered, _ = enrichment_scan
    release = asyncio.Event()
    cleaned = asyncio.Event()

    async def slow_cleanup(**kwargs):
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            await release.wait()
            cleaned.set()

    monkeypatch.setattr(checking, 'run_url_mutations', slow_cleanup)
    task = asyncio.create_task(scan())
    try:
        await asyncio.wait_for(entered.wait(), timeout=1)
        result = (await asyncio.wait_for(asyncio.shield(task), timeout=1))['Local']
        assert result['status'].status == MaigretCheckStatus.CLAIMED
        assert not cleaned.is_set()
        notify.finish.assert_called_once()
    finally:
        release.set()
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await asyncio.wait_for(cleaned.wait(), timeout=1)
