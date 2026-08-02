"""Smoke tests for the Flask web interface in maigret.web.app.

The goal is to catch breakage in the basic user flow (render index, kick off
search, redirect to results) without making real network calls. Heavy maigret
internals are mocked; the report-generation smoke test keeps `save_graph_report`
unmocked so regressions like `nt.options.groups = ...` (AttributeError on a
plain dict) are caught automatically.
"""

import asyncio
import json
import os
import types

import pytest

import maigret
import maigret.report
import maigret.settings
from maigret.result import MaigretCheckResult, MaigretCheckStatus
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
    web_app_module.app.config['SETTINGS_FILE'] = str(tmp_path / 'web_settings.json')

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


def test_results_report_links_open_in_new_tab(client, web_app, monkeypatch):
    """CSV/JSON/PDF/HTML report links must open in a new tab, not navigate away
    from the results page."""

    def fake_task(usernames, options, timestamp):
        web_app.job_results[timestamp] = {
            'status': 'completed',
            'session_folder': f'search_{timestamp}',
            'graph_file': f'search_{timestamp}/combined_graph.html',
            'usernames': usernames,
            'individual_reports': [
                {
                    'username': 'soxoj',
                    'csv_file': f'search_{timestamp}/report_soxoj.csv',
                    'json_file': f'search_{timestamp}/report_soxoj.json',
                    'pdf_file': f'search_{timestamp}/report_soxoj.pdf',
                    'html_file': f'search_{timestamp}/report_soxoj.html',
                    'claimed_profiles': [],
                }
            ],
        }
        web_app.background_jobs[timestamp]['completed'] = True

    monkeypatch.setattr(web_app, 'process_search_task', fake_task)
    monkeypatch.setattr(web_app, 'Thread', _SyncThread)

    post = client.post('/search', data={'usernames': 'soxoj'})
    status_resp = client.get(post.location)
    results_resp = client.get(status_resp.location)
    body = results_resp.get_data(as_text=True)

    for label in ('CSV Report', 'JSON Report', 'PDF Report', 'HTML Report'):
        # crude but effective: the link and its target="_blank" must appear
        # within the same <a> tag, not just somewhere on the page.
        idx = body.index(label)
        tag_start = body.rindex('<a ', 0, idx)
        tag = body[tag_start : idx + len(label)]
        assert 'target="_blank"' in tag, f'{label} link missing target="_blank"'


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


def test_download_report_serves_file_inside_reports_folder(client, web_app, tmp_path):
    """Happy path: a real file inside REPORTS_FOLDER is served back."""
    target = tmp_path / 'session1'
    target.mkdir()
    (target / 'report.json').write_text('{"ok": true}')

    resp = client.get('/reports/session1/report.json')

    assert resp.status_code == 200
    assert resp.get_data() == b'{"ok": true}'


def test_download_report_blocks_dotdot_traversal(client, web_app, tmp_path):
    """A literal ../ in the path must not escape REPORTS_FOLDER."""
    secret = tmp_path.parent / 'outside_secret.txt'
    secret.write_text('SECRET')

    resp = client.get('/reports/..%2Foutside_secret.txt')

    assert resp.status_code == 404
    assert b'SECRET' not in resp.get_data()


def test_download_report_blocks_sibling_prefix_bypass(client, web_app, tmp_path):
    """Regression: the previous startswith() check let `<reports_root>2/secret`
    bypass containment because '/tmp/maigret_reports2'.startswith('/tmp/maigret_reports')
    is True. send_from_directory enforces a real boundary."""
    sibling = tmp_path.parent / (tmp_path.name + '_sibling')
    sibling.mkdir()
    (sibling / 'leak.txt').write_text('LEAK')

    encoded = '..%2F' + sibling.name + '%2Fleak.txt'
    resp = client.get('/reports/' + encoded)

    assert resp.status_code == 404
    assert b'LEAK' not in resp.get_data()


def test_download_report_blocks_absolute_path(client, web_app, tmp_path):
    """An absolute filename must not escape REPORTS_FOLDER."""
    secret = tmp_path.parent / 'abs_secret.txt'
    secret.write_text('ABSOLUTE')

    resp = client.get('/reports/' + str(secret).lstrip('/'))

    assert resp.status_code == 404
    assert b'ABSOLUTE' not in resp.get_data()


def test_search_passes_cloudflare_bypass_from_settings(client, web_app, monkeypatch):
    """If settings.json enables cloudflare_bypass with a valid FlareSolverr module,
    the web search must forward that config to maigret.search via the
    cloudflare_bypass kwarg. Guards the wiring in maigret_search()."""

    captured = {}

    async def fake_search(*args, **kwargs):
        captured.update(kwargs)
        return {}

    def fake_load(self, paths=None):
        self.cloudflare_bypass = {
            "enabled": True,
            "session_prefix": "test-prefix",
            "trigger_protection": ["cf_js_challenge"],
            "modules": [
                {
                    "name": "flaresolverr",
                    "method": "json_api",
                    "url": "http://flare.test:8191/v1",
                    "max_timeout_ms": 60000,
                }
            ],
        }
        return True, ""

    monkeypatch.setattr(maigret.settings.Settings, 'load', fake_load)
    monkeypatch.setattr(maigret, 'search', fake_search)
    monkeypatch.setattr(maigret.report, 'save_graph_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_csv_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_json_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_pdf_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_html_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'generate_report_context', lambda *a, **kw: {})
    monkeypatch.setattr(web_app, 'Thread', _SyncThread)

    client.post('/search', data={'usernames': 'testuser'})

    assert (
        'cloudflare_bypass' in captured
    ), 'maigret.search was not given a cloudflare_bypass kwarg'
    cf = captured['cloudflare_bypass']
    assert cf is not None
    assert cf['session_prefix'] == 'test-prefix'
    assert cf['trigger_protection'] == ['cf_js_challenge']
    assert len(cf['modules']) == 1
    assert cf['modules'][0]['url'] == 'http://flare.test:8191/v1'
    assert cf['modules'][0]['method'] == 'json_api'


def test_search_omits_cloudflare_bypass_when_disabled(client, web_app, monkeypatch):
    """When settings has no cloudflare_bypass (or enabled=false), the kwarg
    must be None so the default checker pipeline runs."""

    captured = {}

    async def fake_search(*args, **kwargs):
        captured.update(kwargs)
        return {}

    def fake_load(self, paths=None):
        # no cloudflare_bypass attribute at all
        return True, ""

    monkeypatch.setattr(maigret.settings.Settings, 'load', fake_load)
    monkeypatch.setattr(maigret, 'search', fake_search)
    monkeypatch.setattr(maigret.report, 'save_graph_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_csv_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_json_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_pdf_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_html_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'generate_report_context', lambda *a, **kw: {})
    monkeypatch.setattr(web_app, 'Thread', _SyncThread)

    client.post('/search', data={'usernames': 'testuser'})

    assert captured.get('cloudflare_bypass') is None


def test_live_scan_streams_found_and_done(client, web_app, monkeypatch):
    """POST /api/scan starts a background scan; GET .../stream yields the per-site
    'found' event and a terminating 'done' event. Guards the SSE + StreamNotify wiring.
    """

    async def fake_search(*args, **kwargs):
        notify = kwargs['query_notify']
        result = MaigretCheckResult(
            username='soxoj',
            site_name='GitHub',
            site_url_user='https://github.com/soxoj',
            status=MaigretCheckStatus.CLAIMED,
            ids_data={'fullname': 'Soxoj', '_extractor': 'x'},
            tags=['dev'],
        )
        notify.update(result)
        return {'GitHub': {'status': result, 'url_user': result.site_url_user}}

    monkeypatch.setattr(maigret, 'search', fake_search)
    # csv/json/pdf report internals are exercised by
    # test_real_report_generation_does_not_crash; here we only care that a
    # completed live scan wires into the same report + results-page flow.
    monkeypatch.setattr(maigret.report, 'save_csv_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_json_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_pdf_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_html_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'generate_report_context', lambda *a, **kw: {})

    start = client.post('/api/scan', data={'usernames': 'soxoj'})
    assert start.status_code == 200
    job_id = start.get_json()['job_id']

    body = client.get(f'/api/scan/{job_id}/stream').get_data(as_text=True)
    events = [
        json.loads(line[6:]) for line in body.splitlines() if line.startswith('data: ')
    ]
    types_seen = [e['type'] for e in events]

    assert 'done' in types_seen
    found = [e for e in events if e['type'] == 'found']
    assert found and found[0]['site'] == 'GitHub'
    # _extractor metadata is stripped from the graph payload
    assert '_extractor' not in found[0]['ids']
    assert found[0]['ids']['fullname'] == 'Soxoj'

    # Regression guard: a completed live scan must still produce the same
    # report files + profile list as the classic /search flow, and hand the
    # browser a redirect to the results page that shows them.
    done_event = next(e for e in events if e['type'] == 'done')
    assert done_event['redirect'] == f'/results/search_{job_id}'

    result = web_app.job_results[job_id]
    assert result['status'] == 'completed'
    reports = result['individual_reports']
    assert reports and reports[0]['username'] == 'soxoj'
    assert reports[0]['claimed_profiles'][0]['site_name'] == 'GitHub'

    results_page = client.get(done_event['redirect']).get_data(as_text=True)
    assert 'GitHub' in results_page
    assert 'CSV Report' in results_page


def test_live_scan_empty_username_rejected(client, web_app):
    resp = client.post('/api/scan', data={'usernames': ''})
    assert resp.status_code == 400


def test_live_scan_stop_unknown_job_404(client, web_app):
    resp = client.post('/api/scan/nope/stop')
    assert resp.status_code == 404


def test_live_start_empty_username_redirects_to_index(client, web_app):
    resp = client.post('/live', data={'usernames': ''})
    assert resp.status_code == 302
    assert resp.location.endswith('/')


def test_live_start_redirects_to_dedicated_live_page(client, web_app, monkeypatch):
    """POST /live starts a job on a NEW page (/live/<job_id>), not inline on
    the index page. That page must show the graph + a Stop button, and must
    NOT unconditionally redirect away on completion (only via the Analyze
    button — see test_live_scan_done_event_offers_redirect_not_auto_navigation)."""

    async def fake_search(*args, **kwargs):
        notify = kwargs['query_notify']
        notify.set_total(0)
        return {}

    monkeypatch.setattr(maigret, 'search', fake_search)

    start = client.post('/live', data={'usernames': 'soxoj'})
    assert start.status_code == 302
    assert start.location.startswith('/live/')
    job_id = start.location.rsplit('/', 1)[1]

    page = client.get(start.location)
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    assert 'id="graph"' in body
    assert 'id="stopBtn"' in body
    assert 'id="analyzeBtn"' in body
    assert job_id in body
    # No unconditional navigation on completion anymore.
    assert 'window.location.href = ev.redirect' not in body

    # Drain the SSE stream so the background thread's queue is consumed and
    # the job entry is cleaned up tidily.
    client.get(f'/api/scan/{job_id}/stream')


def test_live_results_unknown_job_redirects_to_index(client, web_app):
    resp = client.get('/live/does-not-exist')
    assert resp.status_code == 302
    assert resp.location.endswith('/')


def test_live_results_for_finished_job_skips_sse_and_shows_analyze(client, web_app):
    """If the job already finished (e.g. the user reloaded the Live Results
    page), the page must offer the Analyze redirect immediately instead of
    trying to reopen a dead SSE stream."""
    web_app.job_results['finishedjob'] = {
        'status': 'completed',
        'session_folder': 'search_finishedjob',
        'graph_file': 'search_finishedjob/combined_graph.html',
        'usernames': ['soxoj'],
        'individual_reports': [],
        'found_count': 0,
    }

    resp = client.get('/live/finishedjob')
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert 'const doneRedirect = "/results/search_finishedjob";' in body


def test_live_scan_done_event_offers_redirect_not_auto_navigation(
    client, web_app, monkeypatch
):
    """The SSE 'done' payload still carries the redirect URL (consumed by the
    Analyze button), but nothing server- or client-side forces navigation."""

    async def fake_search(*args, **kwargs):
        notify = kwargs['query_notify']
        result = MaigretCheckResult(
            username='soxoj',
            site_name='GitHub',
            site_url_user='https://github.com/soxoj',
            status=MaigretCheckStatus.CLAIMED,
            ids_data={},
        )
        notify.update(result)
        return {'GitHub': {'status': result, 'url_user': result.site_url_user}}

    monkeypatch.setattr(maigret, 'search', fake_search)
    monkeypatch.setattr(maigret.report, 'save_graph_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_csv_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_json_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_pdf_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_html_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'generate_report_context', lambda *a, **kw: {})

    start = client.post('/live', data={'usernames': 'soxoj'})
    job_id = start.location.rsplit('/', 1)[1]

    body = client.get(f'/api/scan/{job_id}/stream').get_data(as_text=True)
    events = [
        json.loads(line[6:]) for line in body.splitlines() if line.startswith('data: ')
    ]
    done_event = next(e for e in events if e['type'] == 'done')
    assert done_event['redirect'] == f'/results/search_{job_id}'

    result = web_app.job_results[job_id]
    assert result['status'] == 'completed'
    assert result['found_count'] == 1
    assert 'started_at' in result


def test_live_scan_stop_mid_scan_keeps_already_found_results(
    client, web_app, monkeypatch
):
    """Regression: clicking Stop while a username's scan is still in-flight
    used to discard every 'found' result already streamed to the live graph,
    because the cancelled search() task never returns its own results dict —
    general_results stayed empty, build_reports never ran, and the browser
    got 'Completed — nothing to analyze.' despite the graph showing hits.

    StreamNotify now keeps a running copy of what it already streamed, and
    that's what gets reported when the task is cancelled mid-scan.
    """

    async def fake_search(*args, **kwargs):
        notify = kwargs['query_notify']
        assert 'ValidActive' in notify.sites, 'site map not wired into StreamNotify'
        found = MaigretCheckResult(
            username='soxoj',
            site_name='ValidActive',
            site_url_user='https://play.google.com/store/apps/developer?id=soxoj',
            status=MaigretCheckStatus.CLAIMED,
        )
        notify.update(found)
        # Simulate task.cancel() firing mid-scan, after this one site was
        # already checked and streamed to the browser but before the other
        # (still in-flight) sites finished.
        raise asyncio.CancelledError()

    monkeypatch.setattr(maigret, 'search', fake_search)
    monkeypatch.setattr(maigret.report, 'save_graph_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_csv_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_json_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_pdf_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_html_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'generate_report_context', lambda *a, **kw: {})

    start = client.post('/live', data={'usernames': 'soxoj'})
    job_id = start.location.rsplit('/', 1)[1]

    body = client.get(f'/api/scan/{job_id}/stream').get_data(as_text=True)
    events = [
        json.loads(line[6:]) for line in body.splitlines() if line.startswith('data: ')
    ]
    types_seen = [e['type'] for e in events]
    assert 'stopped' in types_seen
    found = [e for e in events if e['type'] == 'found']
    assert found and found[0]['site'] == 'ValidActive'

    done_event = next(e for e in events if e['type'] == 'done')
    assert (
        done_event.get('redirect') == f'/results/search_{job_id}'
    ), "Stop must not discard already-found results ('nothing to analyze' bug)"

    result = web_app.job_results[job_id]
    assert result['status'] == 'completed'
    assert result['found_count'] == 1
    assert result['individual_reports'][0]['claimed_profiles'][0]['site_name'] == (
        'ValidActive'
    )


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
    assert (
        result['status'] == 'completed'
    ), f"report generation failed: {result.get('error')!r}"

    # Regression guard: pyvis's default cdn_resources="local" writes a lib/
    # folder relative to the process cwd instead of next to the graph HTML,
    # so the browser 404s fetching lib/bindings/utils.js from /reports/...
    graph_path = os.path.join(web_app.app.config['REPORTS_FOLDER'], result['graph_file'])
    with open(graph_path, encoding='utf-8') as f:
        graph_html = f.read()
    assert 'lib/bindings' not in graph_html
    assert not os.path.exists(os.path.join(os.path.dirname(graph_path), 'lib'))


def test_history_empty_state(client, web_app):
    resp = client.get('/history')
    assert resp.status_code == 200
    assert 'No searches have been run yet.' in resp.get_data(as_text=True)


def test_history_link_present_on_every_page(client, web_app):
    resp = client.get('/')
    body = resp.get_data(as_text=True)
    assert 'href="/history"' in body


def test_new_search_link_present_on_every_page(client, web_app):
    resp = client.get('/history')
    body = resp.get_data(as_text=True)
    assert 'New Search' in body
    assert 'href="/"' in body


def test_history_lists_completed_and_failed_runs(client, web_app):
    web_app.job_results['ts_completed'] = {
        'status': 'completed',
        'session_folder': 'search_ts_completed',
        'graph_file': 'search_ts_completed/combined_graph.html',
        'usernames': ['soxoj', 'alice'],
        'individual_reports': [],
        'found_count': 7,
        'started_at': '2026-07-28 10:00:00',
    }
    web_app.job_results['ts_failed'] = {
        'status': 'failed',
        'error': 'boom',
        'usernames': ['bob'],
        'started_at': '2026-07-28 09:00:00',
    }

    resp = client.get('/history')
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)

    assert '2026-07-28 10:00:00' in body
    assert 'soxoj, alice' in body
    assert '>7<' in body
    assert 'completed' in body
    assert '/results/search_ts_completed' in body

    assert '2026-07-28 09:00:00' in body
    assert 'bob' in body
    assert 'failed' in body

    # Newest run listed first.
    assert body.index('search_ts_completed') < body.index('bob')


def test_build_reports_computes_found_count(web_app, monkeypatch):
    """Regression guard: History reads `found_count` off the dict build_reports
    returns, so it must count claimed profiles across all usernames."""
    monkeypatch.setattr(maigret.report, 'save_csv_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_json_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_pdf_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'save_html_report', lambda *a, **kw: None)
    monkeypatch.setattr(maigret.report, 'generate_report_context', lambda *a, **kw: {})

    claimed = MaigretCheckResult(
        username='soxoj',
        site_name='GitHub',
        site_url_user='https://github.com/soxoj',
        status=MaigretCheckStatus.CLAIMED,
    )
    general_results = [
        (
            'soxoj',
            'username',
            {'GitHub': {'status': claimed, 'url_user': claimed.site_url_user}},
        )
    ]

    report = web_app.build_reports(general_results, ['soxoj'], 'testkey')

    assert report['found_count'] == 1
    assert report['individual_reports'][0]['claimed_profiles'][0]['site_name'] == 'GitHub'


def test_process_search_task_records_started_at_on_success(web_app, monkeypatch):
    async def fake_search_multi(usernames, options):
        return []

    monkeypatch.setattr(web_app, 'search_multiple_usernames', fake_search_multi)
    monkeypatch.setattr(
        web_app,
        'build_reports',
        lambda *a, **kw: {
            'status': 'completed',
            'session_folder': 'x',
            'graph_file': 'x',
            'usernames': [],
            'individual_reports': [],
            'found_count': 0,
        },
    )
    web_app.background_jobs['ts_ok'] = {'completed': False, 'thread': None}

    web_app.process_search_task(['soxoj'], {}, 'ts_ok')

    assert web_app.job_results['ts_ok']['status'] == 'completed'
    assert web_app.job_results['ts_ok']['started_at']


def test_process_search_task_records_started_at_on_failure(web_app, monkeypatch):
    async def failing_search_multi(usernames, options):
        raise RuntimeError('boom')

    monkeypatch.setattr(web_app, 'search_multiple_usernames', failing_search_multi)
    web_app.background_jobs['ts_fail'] = {'completed': False, 'thread': None}

    web_app.process_search_task(['soxoj'], {}, 'ts_fail')

    assert web_app.job_results['ts_fail']['status'] == 'failed'
    assert web_app.job_results['ts_fail']['started_at']


def test_load_settings_defaults_when_no_file(web_app):
    settings = web_app.load_settings()
    assert settings['timeout'] == 10
    assert settings['top_sites'] == 500
    assert settings['tags'] == []
    assert settings['proxy'] == ''
    assert settings['permute'] is False


def test_save_settings_persists_to_file_and_reloads(web_app):
    web_app.save_settings(
        {**web_app.DEFAULT_SETTINGS, 'timeout': 42, 'proxy': '127.0.0.1:9999'}
    )

    assert os.path.exists(web_app.app.config['SETTINGS_FILE'])
    reloaded = web_app.load_settings()
    assert reloaded['timeout'] == 42
    assert reloaded['proxy'] == '127.0.0.1:9999'


def test_settings_update_saves_and_redirects_back(client, web_app):
    resp = client.post(
        '/settings',
        data={
            'timeout': '15',
            'top_sites': '250',
            'tags': ['coding', 'tech'],
            'excluded_tags': ['porn'],
            'site': 'GitHub, Reddit',
            'proxy': '127.0.0.1:1080',
            'permute': 'on',
            'with_domains': 'on',
        },
        headers={'Referer': '/history'},
    )
    assert resp.status_code == 302
    assert resp.headers['Location'] == '/history'

    settings = web_app.load_settings()
    assert settings['timeout'] == 15
    assert settings['top_sites'] == 250
    assert settings['tags'] == ['coding', 'tech']
    assert settings['excluded_tags'] == ['porn']
    assert settings['site_list'] == ['GitHub', 'Reddit']
    assert settings['proxy'] == '127.0.0.1:1080'
    assert settings['permute'] is True
    assert settings['with_domains'] is True
    assert settings['disable_recursive_search'] is False


def test_settings_update_invalid_timeout_falls_back_to_default(client, web_app):
    client.post('/settings', data={'timeout': 'not-a-number', 'top_sites': 'nope'})
    settings = web_app.load_settings()
    assert settings['timeout'] == web_app.DEFAULT_SETTINGS['timeout']
    assert settings['top_sites'] == web_app.DEFAULT_SETTINGS['top_sites']


def test_parse_search_options_uses_saved_settings(web_app):
    web_app.save_settings(
        {
            **web_app.DEFAULT_SETTINGS,
            'timeout': 20,
            'top_sites': 100,
            'proxy': '127.0.0.1:8080',
            'tags': ['gaming'],
            'site_list': ['GitHub'],
            'disable_extracting': True,
        }
    )

    options = web_app.parse_search_options({})

    assert options['timeout'] == 20
    assert options['top_sites'] == 100
    assert options['proxy'] == '127.0.0.1:8080'
    assert options['tags'] == ['gaming']
    assert options['site_list'] == ['GitHub']
    assert options['disable_extracting'] is True
    assert options['all_sites'] is False


def test_parse_search_options_full_mode_ignores_top_sites(web_app):
    options = web_app.parse_search_options({'mode': 'full'})
    assert options['all_sites'] is True


def test_api_sites_returns_site_list(client, web_app):
    resp = client.get('/api/sites')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'sites' in data
    assert isinstance(data['sites'], list)


def test_settings_modal_present_on_every_page(client, web_app):
    resp = client.get('/')
    body = resp.get_data(as_text=True)
    assert 'id="settingsModal"' in body
    assert 'name="timeout"' in body

    resp = client.get('/history')
    body = resp.get_data(as_text=True)
    assert 'id="settingsModal"' in body
