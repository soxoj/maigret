"""Missing optional PDF support must not discard completed web results."""

from pathlib import Path
import queue
import sys

import pytest

import maigret.report as report
from maigret.web import app as web


@pytest.fixture
def isolated_web(tmp_path, monkeypatch):
    monkeypatch.setitem(web.app.config, 'TESTING', True)
    monkeypatch.setitem(web.app.config, 'REPORTS_FOLDER', str(tmp_path))
    monkeypatch.setitem(
        web.app.config, 'MAIGRET_DB_FILE', str(Path(__file__).with_name('db.json'))
    )
    monkeypatch.setattr(web, 'job_results', {})
    monkeypatch.setattr(web, 'background_jobs', {})
    monkeypatch.setattr(web, 'live_jobs', {})
    return web


def completed_results(*names):
    return [(name, 'username', {}) for name in names]


def test_missing_pdf_extra_keeps_other_reports(isolated_web, monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, 'xhtml2pdf', None)
    result = web.build_reports(
        completed_results('alice', 'bob'), ['alice', 'bob'], 'nopdf'
    )
    assert result['status'] == 'completed'
    assert result['found_count'] == 0
    for item in result['individual_reports']:
        assert item['pdf_file'] is None
        assert 'maigret[pdf]' in item['pdf_error']
        for field in ['csv_file', 'json_file', 'html_file']:
            assert (tmp_path / item[field]).is_file()
    assert (tmp_path / result['graph_file']).is_file()


def test_missing_pdf_notice_has_no_broken_download_link(isolated_web, monkeypatch):
    monkeypatch.setitem(sys.modules, 'xhtml2pdf', None)
    web.job_results['nopdf'] = web.build_reports(
        completed_results('alice'), ['alice'], 'nopdf'
    )
    response = web.app.test_client().get('/results/search_nopdf')
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert 'PDF unavailable' in page
    assert 'maigret[pdf]' in page
    assert 'PDF Report</a>' not in page
    assert 'HTML Report</a>' in page
    assert 'CSV Report</a>' in page


def test_available_pdf_keeps_download_link(isolated_web, monkeypatch, tmp_path):
    def save_pdf(filename, context):
        Path(filename).write_bytes(b'%PDF-test')

    monkeypatch.setattr(report, 'save_pdf_report', save_pdf)
    result = web.build_reports(completed_results('alice'), ['alice'], 'pdf')
    assert result['individual_reports'][0]['pdf_file'] == 'search_pdf/report_alice.pdf'
    web.job_results['pdf'] = result
    page = web.app.test_client().get('/results/search_pdf').get_data(as_text=True)
    assert 'PDF Report</a>' in page
    assert 'PDF unavailable' not in page


@pytest.mark.parametrize(
    'error', [RuntimeError('renderer failed'), OSError('disk full')]
)
def test_actual_pdf_generation_errors_are_not_hidden(isolated_web, monkeypatch, error):
    def fail(*args):
        raise error

    monkeypatch.setattr(report, 'save_pdf_report', fail)
    with pytest.raises(type(error), match=str(error)):
        web.build_reports(completed_results('alice'), ['alice'], 'fail')


def test_classic_job_completes_without_pdf_extra(isolated_web, monkeypatch):
    monkeypatch.setitem(sys.modules, 'xhtml2pdf', None)

    async def search(usernames, options):
        return completed_results(*usernames)

    monkeypatch.setattr(web, 'search_multiple_usernames', search)
    web.background_jobs['classic'] = {'completed': False}
    web.process_search_task(['alice'], {}, 'classic')
    assert web.background_jobs['classic']['completed'] is True
    assert web.job_results['classic']['status'] == 'completed'
    assert (
        web.app.test_client()
        .get('/status/classic')
        .location.endswith('/results/search_classic')
    )


def test_live_job_redirects_to_available_reports_without_pdf(isolated_web, monkeypatch):
    monkeypatch.setitem(sys.modules, 'xhtml2pdf', None)

    async def search(job, usernames, options):
        return completed_results(*usernames)

    monkeypatch.setattr(web, '_stream_search', search)
    events: queue.Queue = queue.Queue()
    job = {'queue': events, 'cancelled': False}
    web.live_jobs['live'] = job
    web.run_stream_job('live', ['alice'], {})
    event = events.get_nowait()
    assert event == {'type': 'done', 'redirect': '/results/search_live'}
    assert web.job_results['live']['status'] == 'completed'
