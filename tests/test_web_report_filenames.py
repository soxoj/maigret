"""Web report links must identify the same result as their displayed username."""

from pathlib import Path

import pytest

from maigret.result import MaigretCheckResult, MaigretCheckStatus
from maigret.sites import MaigretSite
from maigret.web import app as web


@pytest.fixture
def local_reports(tmp_path, monkeypatch):
    monkeypatch.setitem(web.app.config, "TESTING", True)
    monkeypatch.setitem(web.app.config, "REPORTS_FOLDER", str(tmp_path))
    monkeypatch.setitem(
        web.app.config, "MAIGRET_DB_FILE", str(Path(__file__).with_name("db.json"))
    )
    monkeypatch.setitem(
        web.app.config, "SETTINGS_FILE", str(tmp_path / "settings.json")
    )
    monkeypatch.setattr(web, "job_results", {})

    def local_pdf(filename, context):
        # PDF is optional. Preserve its per-result content and filename contract.
        Path(filename).write_text(context["username"], encoding="utf-8")

    monkeypatch.setattr(web.maigret.report, "save_pdf_report", local_pdf)
    return web.app.test_client()


def local_results(usernames):
    results = []
    for index, username in enumerate(usernames):
        url = f"https://profiles.example/account-{index}"
        status = MaigretCheckResult(
            username, "Profiles", url, MaigretCheckStatus.CLAIMED
        )
        results.append(
            (
                username,
                "username",
                {
                    "Profiles": {
                        "site": MaigretSite(
                            "Profiles", {"url": "https://profiles.example/{username}"}
                        ),
                        "url_user": url,
                        "status": status,
                    }
                },
            )
        )
    return results


@pytest.mark.parametrize(
    "usernames",
    [
        ["alice", ".alice"],
        ["foo/bar", "foo_bar", "foo_bar_2", "foo\\bar"],
        ["Alice", "alice", "ALICE"],
        ["alice", "alice"],
        ["..", "_", "..."],
        ["alice", "bob"],
    ],
)
def test_each_result_has_independent_downloads(local_reports, tmp_path, usernames):
    result = web.build_reports(local_results(usernames), usernames, "collision")
    web.job_results["collision"] = result
    assert result["found_count"] == len(usernames)
    assert [report["username"] for report in result["individual_reports"]] == usernames
    assert local_reports.get("/results/search_collision").status_code == 200

    for extension in ["csv", "json", "html", "pdf"]:
        paths = [report[f"{extension}_file"] for report in result["individual_reports"]]
        # Check the namespace Windows and other case-insensitive filesystems use,
        # even when this regression runs on a case-sensitive host.
        assert len({path.casefold() for path in paths}) == len(usernames)
        for index, path in enumerate(paths):
            disk_path = tmp_path / path
            assert (
                disk_path.resolve().parent == (tmp_path / "search_collision").resolve()
            )
            response = local_reports.get(f"/reports/{path}")
            assert response.status_code == 200
            body = response.get_data(as_text=True)
            if extension == "pdf":
                assert body == usernames[index]
            else:
                assert f"https://profiles.example/account-{index}" in body
                for other in range(len(usernames)):
                    if other != index:
                        assert f"https://profiles.example/account-{other}" not in body


def test_unambiguous_filenames_stay_unchanged(local_reports):
    result = web.build_reports(
        local_results(["alice", "bob"]), ["alice", "bob"], "plain"
    )
    for report in result["individual_reports"]:
        for extension in ["csv", "json", "html", "pdf"]:
            assert (
                report[f"{extension}_file"]
                == f"search_plain/report_{report['username']}.{extension}"
            )
