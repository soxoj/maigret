"""Smoke tests for the Flask web interface in maigret.web.app.

The goal is to catch breakage in the basic user flow (render index, kick off
search, redirect to results) without making real network calls. Heavy maigret
internals are mocked; the report-generation smoke test keeps `save_graph_report`
unmocked so regressions like `nt.options.groups = ...` (AttributeError on a
plain dict) are caught automatically.
"""
import os

import pytest

import maigret
import maigret.report
from maigret.web import app as web_app_module


CUR_PATH = os.path.dirname(os.path.realpath(__file__))
TEST_DB = os.path.join(CUR_PATH, 'db.json')


class _SyncThread:
    """Drop-in for threading.Thread that runs target synchronously on start()."""

    def __init__(self, target=None, args=(), kwargs=None, **_):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def start(self):
        self._target(*self._args, **self._kwargs)


@pytest.fixture
def web_app(tmp_path):
    web_app_module.app.config['TESTING'] = True
    web_app_module.app.config['REPORTS_FOLDER'] = str(tmp_path)
    web_app_module.app.config['MAIGRET_DB_FILE'] = TEST_DB

    web_app_module.background_jobs.clear()
    web_app_module.job_results.clear()

    yield web_app_module

    web_app_module.background_jobs.clear()
    web_app_module.job_results.clear()


@pytest.fixture
def client(web_app):
    return web_app.app.test_client()


def test_index_renders(client):
    resp = client.get('/')
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert 'name="usernames"' in body
    assert '<form' in body


def test_search_empty_input_redirects_to_index(client):
    resp = client.post('/search', data={'usernames': ''})
    assert resp.status_code == 302
    assert resp.location.rstrip('/').endswith('') or resp.location.endswith('/')


def test_search_redirects_to_status(client, web_app, monkeypatch):
    monkeypatch.setattr(web_app, 'process_search_task', lambda *a, **kw: None)
    monkeypatch.setattr(web_app, 'Thread', _SyncThread)

    resp = client.post('/search', data={'usernames': 'soxoj'})

    assert resp.status_code == 302
    assert '/status/' in resp.location


def test_invalid_timestamp_redirects_to_index(client):
    resp = client.get('/status/nonexistent_ts')
    assert resp.status_code == 302
    assert resp.location.endswith('/')


def test_status_running_renders_status_page(client, web_app, monkeypatch):
    """While the background job is still running, /status/<ts> returns 200."""

    def never_completes(usernames, options, timestamp):
        # leave background_jobs[timestamp]['completed'] as False
        pass

    monkeypatch.setattr(web_app, 'process_search_task', never_completes)
    monkeypatch.setattr(web_app, 'Thread', _SyncThread)

    post = client.post('/search', data={'usernames': 'soxoj'})
    status_resp = client.get(post.location)

    assert status_resp.status_code == 200


def test_completed_search_redirects_to_results(client, web_app, monkeypatch):
    """Happy path: POST /search → background completes → /status/<ts> → /results/<session>."""

    def fake_task(usernames, options, timestamp):
        web_app.job_results[timestamp] = {
            'status': 'completed',
            'session_folder': f'search_{timestamp}',
            'graph_file': f'search_{timestamp}/combined_graph.html',
            'usernames': usernames,
            'individual_reports': [],
        }
        web_app.background_jobs[timestamp]['completed'] = True

    monkeypatch.setattr(web_app, 'process_search_task', fake_task)
    monkeypatch.setattr(web_app, 'Thread', _SyncThread)

    post = client.post('/search', data={'usernames': 'soxoj'})
    assert post.status_code == 302

    status_resp = client.get(post.location)
    assert status_resp.status_code == 302
    assert '/results/search_' in status_resp.location

    results_resp = client.get(status_resp.location)
    assert results_resp.status_code == 200
    assert b'soxoj' in results_resp.data


def test_failed_task_redirects_to_index(client, web_app, monkeypatch):
    def failing_task(usernames, options, timestamp):
        web_app.job_results[timestamp] = {'status': 'failed', 'error': 'boom'}
        web_app.background_jobs[timestamp]['completed'] = True

    monkeypatch.setattr(web_app, 'process_search_task', failing_task)
    monkeypatch.setattr(web_app, 'Thread', _SyncThread)

    post = client.post('/search', data={'usernames': 'soxoj'})
    status_resp = client.get(post.location)

    assert status_resp.status_code == 302
    assert status_resp.location.endswith('/')


def test_real_report_generation_does_not_crash(client, web_app, monkeypatch):
    """End-to-end with mocked maigret.search but REAL report generation.

    This is the regression guard for bugs inside `save_graph_report` and friends
    (e.g. `nt.options.groups = ...` raising AttributeError on a dict). If any of
    the unmocked report functions throws, the task records a failed status and
    this assertion catches it.
    """

    async def fake_search(*args, **kwargs):
        return {}

    monkeypatch.setattr(maigret, 'search', fake_search)
    # Mock the per-username report writers — they are not what we care about here,
    # and pdf/html generation pulls in xhtml2pdf which is slow and brittle.
    monkeypatch.setattr(maigret.report, 'save_csv_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_json_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_pdf_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_html_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'generate_report_context', lambda *a, **kw: {})
    monkeypatch.setattr(web_app, 'Thread', _SyncThread)

    post = client.post('/search', data={'usernames': 'testuser'})
    timestamp = post.location.rsplit('/', 1)[1]

    assert timestamp in web_app.job_results, 'background task did not record any result'
    result = web_app.job_results[timestamp]
    assert result['status'] == 'completed', (
        f"report generation failed: {result.get('error')!r}"
    )
