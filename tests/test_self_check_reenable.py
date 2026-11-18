"""A disabled entry needs two conclusive control results before re-enabling."""

import logging
from unittest.mock import patch

import pytest

from maigret.checking import self_check
from maigret.errors import CheckError
from maigret.result import MaigretCheckResult, MaigretCheckStatus
from maigret.sites import MaigretDatabase, MaigretSite


@pytest.mark.asyncio
@pytest.mark.parametrize('disabled', [False, True])
@pytest.mark.parametrize('auto_disable', [False, True])
@pytest.mark.parametrize('claimed', list(MaigretCheckStatus))
@pytest.mark.parametrize('unclaimed', list(MaigretCheckStatus))
async def test_self_check_state_needs_conclusive_evidence(
    disabled, auto_disable, claimed, unclaimed
):
    site = MaigretSite(
        'Fixture',
        {
            'url': 'https://example.test/{username}',
            'checkType': 'status_code',
            'usernameClaimed': 'alice',
            'usernameUnclaimed': 'missing',
            'disabled': disabled,
        },
    )
    db = MaigretDatabase()
    db.update_site(site)

    async def result_for(username, **kwargs):
        status = claimed if username == 'alice' else unclaimed
        error = (
            CheckError('Rate limited', '429 status code')
            if status == MaigretCheckStatus.UNKNOWN
            else None
        )
        return {
            'Fixture': {
                'status': MaigretCheckResult(
                    username, 'Fixture', '', status, error=error
                ),
                'http_status': 429 if error else 200,
            }
        }

    with patch('maigret.checking.maigret', side_effect=result_for):
        result = await self_check(
            db,
            {'Fixture': site},
            logging.getLogger(__name__),
            silent=True,
            no_progressbar=True,
            auto_disable=auto_disable,
        )

    passes = (
        claimed == MaigretCheckStatus.CLAIMED
        and unclaimed == MaigretCheckStatus.AVAILABLE
    )
    conclusively_wrong = claimed not in (
        MaigretCheckStatus.CLAIMED,
        MaigretCheckStatus.UNKNOWN,
    ) or unclaimed not in (MaigretCheckStatus.AVAILABLE, MaigretCheckStatus.UNKNOWN)
    expected = (
        disabled
        if not auto_disable
        else (not passes if disabled else conclusively_wrong)
    )
    assert site.disabled is expected
    assert result['needs_update'] is (disabled != expected)
    if not passes:
        assert result['results'][0]['issues']
