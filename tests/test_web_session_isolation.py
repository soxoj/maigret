"""Independent classic web jobs must not share their result and file keys."""

from datetime import datetime
from pathlib import Path

import pytest

from maigret.result import MaigretCheckResult, MaigretCheckStatus
from maigret.sites import MaigretSite
from maigret.web import app as web


class FrozenDateTime:
    @classmethod
    def now(cls):
        return datetime(2026, 11, 19, 12, 0, 0)


class DeferredThread:
    def __init__(self, target, args):
        self.target = target
        self.args = args

    def start(self):
        pass

    def complete(self):
        self.target(*self.args)


@pytest.fixture
def isolated_web(tmp_path, monkeypatch):
    monkeypatch.setitem(web.app.config, "TESTING", True)
    monkeypatch.setitem(web.app.config, "REPORTS_FOLDER", str(tmp_path))
    monkeypatch.setitem(
        web.app.config, "MAIGRET_DB_FILE", str(Path(__file__).with_name("db.json"))
    )
    monkeypatch.setitem(
        web.app.config, "SETTINGS_FILE", str(tmp_path / "settings.json")
    )
    monkeypatch.setattr(web, "datetime", FrozenDateTime)
    monkeypatch.setattr(web, "Thread", DeferredThread)
    monkeypatch.setattr(web, "background_jobs", {})
    monkeypatch.setattr(web, "job_results", {})
    return web.app.test_client()


def test_same_tick_searches_keep_independent_job_records(isolated_web):
    first = isolated_web.post("/search", data={"usernames": "alice"})
    second = isolated_web.post("/search", data={"usernames": "bob"})
    assert first.location != second.location
    assert len(web.background_jobs) == 2
    assert len({job["thread"].args[2] for job in web.background_jobs.values()}) == 2
    assert all(not job["completed"] for job in web.background_jobs.values())


@pytest.mark.parametrize("reverse_completion", [False, True])
def test_same_tick_searches_keep_results_and_reports_separate(
    isolated_web, monkeypatch, tmp_path, reverse_completion
):
    async def local_search(username, options, query_notify=None):
        url = f"https://profiles.example/{username}"
        return {
            "Profiles": {
                "site": MaigretSite(
                    "Profiles", {"url": "https://profiles.example/{username}"}
                ),
                "url_user": url,
                "status": MaigretCheckResult(
                    username, "Profiles", url, MaigretCheckStatus.CLAIMED
                ),
            }
        }

    monkeypatch.setattr(web, "maigret_search", local_search)
    # PDF is an optional dependency; all other report writers remain real.
    monkeypatch.setattr(web.maigret.report, "save_pdf_report", lambda *args: None)
    responses = [
        isolated_web.post("/search", data={"usernames": username})
        for username in ["alice", "bob"]
    ]
    assert responses[0].location != responses[1].location
    keys = [response.location.rsplit("/", 1)[1] for response in responses]
    order = list(reversed(keys)) if reverse_completion else keys
    web.background_jobs[order[0]]["thread"].complete()
    assert web.background_jobs[order[0]]["completed"]
    assert not web.background_jobs[order[1]]["completed"]
    assert isolated_web.get(f"/status/{order[1]}").status_code == 200
    web.background_jobs[order[1]]["thread"].complete()

    assert len(web.job_results) == 2
    assert len({result["session_folder"] for result in web.job_results.values()}) == 2
    for username, other, key in [("alice", "bob", keys[0]), ("bob", "alice", keys[1])]:
        status = isolated_web.get(f"/status/{key}")
        assert status.location == f"/results/search_{key}"
        page = isolated_web.get(status.location).get_data(as_text=True)
        assert f"https://profiles.example/{username}" in page
        assert f"https://profiles.example/{other}" not in page
        result = web.job_results[key]
        report = result["individual_reports"][0]
        assert report["username"] == username
        download = isolated_web.get(f"/reports/{report['json_file']}")
        assert download.status_code == 200
        assert f"https://profiles.example/{username}" in download.get_data(as_text=True)
        graph = (tmp_path / result["graph_file"]).read_text(encoding="utf-8")
        assert f"https://profiles.example/{username}" in graph
        assert f"https://profiles.example/{other}" not in graph


def test_existing_timestamp_session_still_resolves(isolated_web):
    key = "20261118_235959"
    web.background_jobs[key] = {"completed": True}
    web.job_results[key] = {
        "status": "completed",
        "session_folder": f"search_{key}",
        "graph_file": f"search_{key}/combined_graph.html",
        "usernames": ["alice"],
        "individual_reports": [],
    }
    response = isolated_web.get(f"/status/{key}")
    assert response.location == f"/results/search_{key}"
    assert isolated_web.get(response.location).status_code == 200
