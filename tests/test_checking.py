from mock import Mock
import pytest

from maigret import search


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


@pytest.mark.slow
@pytest.mark.asyncio
async def test_checking_by_post_message(httpserver, local_test_db):
    sites_dict = local_test_db.sites_dict

    import json

    # Existing user: API responds with {"exists": true}
    httpserver.expect_request(
        '/api/check',
        method='POST',
        json={"username": "claimed", "type": "lookup"},
    ).respond_with_data(
        json.dumps({"exists": True}), content_type="application/json"
    )

    # Non-existing user: API responds with {"msg": "not found"}
    httpserver.expect_request(
        '/api/check',
        method='POST',
        json={"username": "unclaimed", "type": "lookup"},
    ).respond_with_data(
        json.dumps({"msg": "not found"}), content_type="application/json"
    )

    result = await search('claimed', site_dict=sites_dict, logger=Mock())
    assert result['PostMessage']['status'].is_found() is True

    result = await search('unclaimed', site_dict=sites_dict, logger=Mock())
    assert result['PostMessage']['status'].is_found() is False
