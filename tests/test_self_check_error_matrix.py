"""Private compatibility checks for qualified self-check state fixes."""

import logging
from unittest.mock import patch

import pytest

from maigret.checking import self_check
from maigret.result import MaigretCheckResult, MaigretCheckStatus
from maigret.sites import MaigretDatabase, MaigretSite


@pytest.mark.asyncio
@pytest.mark.parametrize('disabled', [False, True])
@pytest.mark.parametrize('auto_disable', [False, True])
@pytest.mark.parametrize('failure_stage', ['alice', 'missing'])
@pytest.mark.parametrize('failure_kind', ['raise', 'missing', 'malformed'])
async def test_self_check_failure_boundary_state(
    disabled, auto_disable, failure_stage, failure_kind, tmp_path
):
    db = MaigretDatabase()
    site = MaigretSite(
        'Fixture',
        {
            'url': 'https://example.test/{username}',
            'usernameClaimed': 'alice',
            'usernameUnclaimed': 'missing',
            'disabled': disabled,
        },
    )
    db.update_site(site)

    async def result_for(username, **kwargs):
        if username == failure_stage:
            if failure_kind == 'raise':
                raise RuntimeError('Synthetic checker failure')
            if failure_kind == 'missing':
                return {}
            return {'Fixture': {}}
        status = (
            MaigretCheckStatus.CLAIMED
            if username == 'alice'
            else MaigretCheckStatus.AVAILABLE
        )
        return {
            'Fixture': {'status': MaigretCheckResult(username, 'Fixture', '', status)}
        }

    with patch('maigret.checking.maigret', side_effect=result_for):
        result = await self_check(
            db,
            {'Fixture': site},
            logging.getLogger(__name__),
            auto_disable=auto_disable,
            silent=True,
            no_progressbar=True,
        )

    expected = True if auto_disable else disabled
    assert site.disabled is expected
    assert result['needs_update'] is (disabled != expected)
    assert len(result['results']) == 1
    assert result['results'][0]['site_name'] == 'Fixture'
    assert result['results'][0]['issues']
    target = tmp_path / 'db.json'
    db.save_to_file(str(target))
    saved = MaigretDatabase().load_from_file(str(target))
    assert saved.sites_dict['Fixture'].disabled is expected
