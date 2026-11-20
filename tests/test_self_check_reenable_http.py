"""Exercise disabled-site recovery through the real HTTP checking path."""

import logging

import pytest

from maigret.checking import self_check
from maigret.sites import MaigretDatabase, MaigretSite


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'claimed_status,unclaimed_status,expected_disabled',
    [
        (200, 404, False),
        (429, 404, True),
        (200, 429, True),
        (429, 429, True),
        (404, 404, True),
    ],
)
async def test_disabled_recovery_real_http(
    httpserver, claimed_status, unclaimed_status, expected_disabled, tmp_path
):
    for username, status in [('alice', claimed_status), ('missing', unclaimed_status)]:
        httpserver.expect_request('/' + username).respond_with_data(
            'profile' if status == 200 else 'unavailable', status=status
        )
    site = MaigretSite(
        'Loopback',
        {
            'url': httpserver.url_for('/{username}'),
            'urlMain': httpserver.url_for('/'),
            'checkType': 'status_code',
            'usernameClaimed': 'alice',
            'usernameUnclaimed': 'missing',
            'disabled': True,
        },
    )
    db = MaigretDatabase()
    db.update_site(site)
    result = await self_check(
        db,
        {'Loopback': site},
        logging.getLogger(__name__),
        silent=True,
        no_progressbar=True,
        auto_disable=True,
    )
    assert site.disabled is expected_disabled
    assert result['needs_update'] is (not expected_disabled)
    assert result['total_issues'] == int(expected_disabled)
    assert {request.path for request, _ in httpserver.log} == {'/alice', '/missing'}
    target = tmp_path / 'database.json'
    db.save_to_file(str(target))
    restored = MaigretDatabase().load_from_file(str(target))
    assert restored.sites_dict['Loopback'].disabled is expected_disabled
