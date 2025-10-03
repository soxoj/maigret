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


# CloudFlare bypass tests
@pytest.mark.asyncio
async def test_cloudscraper_checker_initialization():
    """Test CloudscraperChecker can be initialized with proper parameters"""
    from maigret.checking import CloudscraperChecker
    from mock import Mock

    logger = Mock()
    checker = CloudscraperChecker(logger=logger)

    assert checker is not None
    assert checker.logger == logger


@pytest.mark.asyncio
async def test_cloudscraper_checker_prepare():
    """Test CloudscraperChecker prepare method stores request parameters"""
    from maigret.checking import CloudscraperChecker
    from mock import Mock

    checker = CloudscraperChecker(logger=Mock())
    url = "https://example.com/test"
    headers = {"User-Agent": "test"}

    checker.prepare(url=url, headers=headers, timeout=10, method='get')

    assert checker.url == url
    assert checker.headers == headers
    assert checker.timeout == 10
    assert checker.method == 'get'


@pytest.mark.asyncio
async def test_cloudscraper_checker_check_success():
    """Test CloudscraperChecker.check() returns proper format on success"""
    from maigret.checking import CloudscraperChecker
    from unittest.mock import patch, MagicMock
    from mock import Mock

    checker = CloudscraperChecker(logger=Mock())
    checker.prepare(url="https://example.com", headers={}, timeout=10)

    # Mock cloudscraper response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html>User Profile</html>"
    mock_response.apparent_encoding = "utf-8"
    mock_response.encoding = "utf-8"

    with patch('cloudscraper.create_scraper') as mock_scraper:
        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_scraper.return_value = mock_session

        html_text, status_code, error = await checker.check()

        assert html_text == "<html>User Profile</html>"
        assert status_code == 200
        assert error is None


@pytest.mark.asyncio
async def test_cloudscraper_checker_check_timeout():
    """Test CloudscraperChecker.check() handles timeout errors"""
    from maigret.checking import CloudscraperChecker
    from maigret.errors import CheckError
    from unittest.mock import patch, MagicMock
    from mock import Mock

    checker = CloudscraperChecker(logger=Mock())
    checker.prepare(url="https://example.com", headers={}, timeout=1)

    with patch('cloudscraper.create_scraper') as mock_scraper:
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Connection timeout")
        mock_scraper.return_value = mock_session

        html_text, status_code, error = await checker.check()

        assert html_text == ''
        assert status_code == 0
        assert error is not None
        assert isinstance(error, CheckError)


@pytest.mark.asyncio
async def test_cloudflare_error_detection():
    """Test that Cloudflare errors are properly detected"""
    from maigret.errors import detect

    cloudflare_html = '<title>Attention Required! | Cloudflare</title>'
    error = detect(cloudflare_html)

    assert error is not None
    assert error.type == 'Captcha'
    assert 'Cloudflare' in error.desc
