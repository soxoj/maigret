"""A lost SSE connection must not orphan a running scan."""

import asyncio
import json
import queue
import threading
from typing import Any

import pytest

from maigret.web import app as web


@pytest.fixture
def isolated_jobs(monkeypatch):
    monkeypatch.setitem(web.app.config, 'TESTING', True)
    monkeypatch.setattr(web, 'live_jobs', {})
    monkeypatch.setattr(web, 'job_results', {})


def seed_job(key='local') -> dict[str, Any]:
    job = {'queue': queue.Queue(), 'cancelled': False, 'loop': None, 'task': None}
    web.live_jobs[key] = job
    return job


def disconnect(client, key, job):
    job['queue'].put({'type': 'progress', 'checked': 1, 'total': 2})
    response = client.get(f'/api/scan/{key}/stream', buffered=False)
    assert response.status_code == 200
    assert b'progress' in next(iter(response.response))
    response.close()


def test_disconnect_keeps_active_scan_controllable(isolated_jobs):
    job = seed_job()
    with web.app.test_client() as client:
        disconnect(client, 'local', job)
        assert web.live_jobs.get('local') is job
        assert client.get('/live/local').status_code == 200
        assert client.post('/api/scan/local/stop').status_code == 200
        assert job['cancelled'] is True


def test_reconnect_receives_remaining_events_and_cleans_finished_job(
    isolated_jobs, monkeypatch
):
    job = seed_job()

    async def empty_search(*args):
        return []

    monkeypatch.setattr(web, '_stream_search', empty_search)
    with web.app.test_client() as client:
        disconnect(client, 'local', job)
        job['queue'].put({'type': 'progress', 'checked': 2, 'total': 2})
        response = client.get('/api/scan/local/stream', buffered=False)
        assert response.status_code == 200
        web.run_stream_job('local', ['local-demo'], {})
        # A new subscriber is attached, so completion leaves cleanup to it.
        assert web.live_jobs.get('local') is job
        events = [
            json.loads(line[6:])
            for line in response.get_data(as_text=True).splitlines()
            if line.startswith('data: ')
        ]
        assert events == [
            {'type': 'progress', 'checked': 2, 'total': 2},
            {'type': 'done'},
        ]
        assert 'local' not in web.live_jobs


@pytest.mark.parametrize('outcome', ['results', 'empty', 'report_error'])
def test_detached_job_is_cleaned_when_worker_finishes(
    isolated_jobs, monkeypatch, outcome
):
    job = seed_job()

    async def search(*args):
        return [] if outcome == 'empty' else [('local-demo', 'username', {})]

    def reports(*args):
        if outcome == 'report_error':
            raise OSError('local report error')
        return {'status': 'completed', 'session_folder': 'search_local'}

    monkeypatch.setattr(web, '_stream_search', search)
    monkeypatch.setattr(web, 'build_reports', reports)
    with web.app.test_client() as client:
        disconnect(client, 'local', job)
    # A cleanup test must establish the detached job still exists before work ends.
    assert web.live_jobs.get('local') is job
    web.run_stream_job('local', ['local-demo'], {})
    assert 'local' not in web.live_jobs
    assert job['queue'].get_nowait()['type'] == 'done'
    if outcome == 'results':
        assert web.job_results['local']['session_folder'] == 'search_local'


def test_reconnect_after_successful_detached_completion_gets_result_link(isolated_jobs):
    web.job_results['finished'] = {
        'status': 'completed',
        'session_folder': 'search_finished',
    }
    with web.app.test_client() as client:
        response = client.get('/api/scan/finished/stream')
        assert response.status_code == 200
        assert response.mimetype == 'text/event-stream'
        event = json.loads(response.get_data(as_text=True).strip()[6:])
        assert event == {'type': 'done', 'redirect': '/results/search_finished'}
    assert 'finished' not in web.live_jobs


def test_lost_terminal_queue_event_is_replayed_to_another_connection(
    isolated_jobs, monkeypatch
):
    job = seed_job()

    async def empty_search(*args):
        return []

    monkeypatch.setattr(web, '_stream_search', empty_search)
    web.run_stream_job('local', ['local-demo'], {})
    # Model an older socket consuming done and then failing to deliver it.
    assert job['queue'].get_nowait() == {'type': 'done'}

    def no_more_queue_events(*args, **kwargs):
        raise queue.Empty

    monkeypatch.setattr(job['queue'], 'get', no_more_queue_events)
    with web.app.test_client() as client:
        response = client.get('/api/scan/local/stream')
        assert response.status_code == 200
        assert '"type": "done"' in response.get_data(as_text=True)
    assert 'local' not in web.live_jobs


def test_finished_stream_still_cleans_up(isolated_jobs):
    job = seed_job()
    job['done_event'] = {'type': 'done'}
    job['queue'].put({'type': 'done'})
    with web.app.test_client() as client:
        response = client.get('/api/scan/local/stream')
        assert '"type": "done"' in response.get_data(as_text=True)
    assert 'local' not in web.live_jobs


def test_stop_after_disconnect_cancels_actual_worker(isolated_jobs, monkeypatch):
    started = threading.Event()
    cancelled = threading.Event()
    job = seed_job()

    async def search(username, options, query_notify=None):
        query_notify.q.put({'type': 'progress', 'checked': 1, 'total': 2})
        started.set()
        try:
            await asyncio.Future()
        finally:
            cancelled.set()

    monkeypatch.setattr(web, 'maigret_search', search)
    worker = threading.Thread(
        target=web.run_stream_job, args=('local', ['local-demo'], {})
    )
    worker.start()
    try:
        assert started.wait(3)
        with web.app.test_client() as client:
            response = client.get('/api/scan/local/stream', buffered=False)
            assert b'progress' in next(iter(response.response))
            response.close()
            assert client.post('/api/scan/local/stop').status_code == 200
        assert cancelled.wait(3)
        worker.join(3)
        assert not worker.is_alive()
        assert 'local' not in web.live_jobs
    finally:
        if worker.is_alive():
            job['loop'].call_soon_threadsafe(job['task'].cancel)
            worker.join(3)
        assert not worker.is_alive()
