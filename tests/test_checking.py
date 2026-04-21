import asyncio
import logging

from mock import Mock
import pytest

from maigret import search
from maigret.checking import check_site_for_username, process_site_result
from maigret.result import MaigretCheckResult, MaigretCheckStatus


def site_result_except(server, username, **kwargs):
    query = f'id={username}'
    server.expect_request('/url', query_string=query).respond_with_data(**kwargs)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_checking_by_status_code(httpserver, local_test_db):
    sites_dict = local_test_db.sites_dict

    site_result_except(httpserver, 'claimed', status=200)
    site_result_except(httpserver, 'unclaimed', status=404)

    result = await search('claimed', site_dict=sites_dict, logger=Mock())
    assert result['StatusCode']['status'].is_found() is True

    result = await search('unclaimed', site_dict=sites_dict, logger=Mock())
    assert result['StatusCode']['status'].is_found() is False


@pytest.mark.slow
@pytest.mark.asyncio
async def test_checking_by_message_positive_full(httpserver, local_test_db):
    sites_dict = local_test_db.sites_dict

    site_result_except(httpserver, 'claimed', response_data="user profile")
    site_result_except(httpserver, 'unclaimed', response_data="404 not found")

    result = await search('claimed', site_dict=sites_dict, logger=Mock())
    assert result['Message']['status'].is_found() is True

    result = await search('unclaimed', site_dict=sites_dict, logger=Mock())
    assert result['Message']['status'].is_found() is False


@pytest.mark.slow
@pytest.mark.asyncio
async def test_checking_by_message_positive_part(httpserver, local_test_db):
    sites_dict = local_test_db.sites_dict

    site_result_except(httpserver, 'claimed', response_data="profile")
    site_result_except(httpserver, 'unclaimed', response_data="404")

    result = await search('claimed', site_dict=sites_dict, logger=Mock())
    assert result['Message']['status'].is_found() is True

    result = await search('unclaimed', site_dict=sites_dict, logger=Mock())
    assert result['Message']['status'].is_found() is False


@pytest.mark.slow
@pytest.mark.asyncio
async def test_checking_by_message_negative(httpserver, local_test_db):
    sites_dict = local_test_db.sites_dict

    site_result_except(httpserver, 'claimed', response_data="")
    site_result_except(httpserver, 'unclaimed', response_data="user 404")

    result = await search('claimed', site_dict=sites_dict, logger=Mock())
    assert result['Message']['status'].is_found() is False

    result = await search('unclaimed', site_dict=sites_dict, logger=Mock())
    assert result['Message']['status'].is_found() is True


def test_process_site_result_threads_response_time(local_test_db):
    """process_site_result must thread the response_time kwarg into the result's query_time."""
    site = local_test_db.sites_dict['StatusCode']
    results_info = {
        'username': 'claimed',
        'parsing_enabled': False,
        'url_user': site.url.replace('{username}', 'claimed'),
        'status': None,
        'rank': 0,
        'url_main': site.url_main,
        'ids_data': {},
    }
    response = ('body', 200, None)
    logger = logging.getLogger('test')
    query_notify = Mock()

    out = process_site_result(
        response, query_notify, logger, results_info, site,
        response_time=1.234,
    )
    assert out['status'].query_time == pytest.approx(1.234)


def test_process_site_result_defaults_response_time_to_none(local_test_db):
    """Omitting response_time keeps query_time as None (backward compatible)."""
    site = local_test_db.sites_dict['StatusCode']
    results_info = {
        'username': 'claimed',
        'parsing_enabled': False,
        'url_user': site.url.replace('{username}', 'claimed'),
        'status': None,
        'rank': 0,
        'url_main': site.url_main,
        'ids_data': {},
    }
    out = process_site_result(
        ('body', 200, None), Mock(), logging.getLogger('test'), results_info, site,
    )
    assert out['status'].query_time is None


@pytest.mark.slow
@pytest.mark.asyncio
async def test_query_time_populated_from_http_check(httpserver, local_test_db):
    """check_site_for_username measures HTTP round-trip and populates query_time."""
    sites_dict = local_test_db.sites_dict

    # Delay the response on the test HTTP server to produce a measurable query_time.
    DELAY = 0.25

    def delayed_handler(request):
        import time as _time
        _time.sleep(DELAY)
        from werkzeug.wrappers import Response
        return Response('ok', status=200)

    httpserver.expect_request('/url', query_string='id=claimed').respond_with_handler(delayed_handler)

    result = await search('claimed', site_dict={'StatusCode': sites_dict['StatusCode']}, logger=Mock())
    status = result['StatusCode']['status']
    assert status.is_found() is True
    assert isinstance(status.query_time, float)
    assert status.query_time >= DELAY
    # Upper bound: the measurement should not wildly exceed the server delay.
    assert status.query_time < DELAY + 5.0
