"""Saving depends on changed site flags, not the net number of disabled sites."""

import logging
from unittest.mock import patch

import pytest

from maigret.checking import self_check
from maigret.result import MaigretCheckResult, MaigretCheckStatus
from maigret.sites import MaigretDatabase, MaigretSite


@pytest.mark.asyncio
@pytest.mark.parametrize('auto_disable', [False, True])
@pytest.mark.parametrize(
    'initial', [(True, False), (True, True), (False, False), (False, True)]
)
async def test_self_check_reports_all_changed_disabled_flags(
    auto_disable, initial, tmp_path
):
    db = MaigretDatabase()
    sites = {}
    for name, disabled in zip(('Recovered', 'Broken'), initial):
        site = MaigretSite(
            name,
            {
                'url': 'https://example.test/{username}',
                'usernameClaimed': 'alice',
                'usernameUnclaimed': 'missing',
                'disabled': disabled,
            },
        )
        sites[name] = site
        db.update_site(site)

    async def result_for(username, site_dict, **kwargs):
        site = next(iter(site_dict.values()))
        claimed = site.name == 'Broken' or username == 'alice'
        status = MaigretCheckStatus.CLAIMED if claimed else MaigretCheckStatus.AVAILABLE
        return {
            site.name: {
                'status': MaigretCheckResult(username, site.name, '', status),
                'http_status': 200 if claimed else 404,
            }
        }

    with patch('maigret.checking.maigret', side_effect=result_for):
        result = await self_check(
            db,
            sites,
            logging.getLogger(__name__),
            silent=True,
            auto_disable=auto_disable,
            no_progressbar=True,
        )

    expected = (False, True) if auto_disable else initial
    assert tuple(site.disabled for site in sites.values()) == expected
    assert result['needs_update'] is (expected != initial)
    if result['needs_update']:
        target = tmp_path / 'database.json'
        db.save_to_file(str(target))
        saved = MaigretDatabase().load_from_file(str(target)).sites_dict
        assert tuple(saved[name].disabled for name in sites) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize('answer', ['y', 'n'])
async def test_cli_offers_to_save_balanced_changes(answer, tmp_path, monkeypatch):
    import importlib
    import json

    cli = importlib.import_module('maigret.maigret')
    target = tmp_path / 'database.json'
    original = {
        'sites': {
            name: {
                'url': 'https://example.test/{username}',
                'usernameClaimed': 'alice',
                'usernameUnclaimed': 'missing',
                'disabled': disabled,
            }
            for name, disabled in [('Recovered', True), ('Broken', False)]
        },
        'engines': {},
        'tags': [],
    }
    target.write_text(json.dumps(original), encoding='utf-8')

    async def result_for(username, site_dict, **kwargs):
        site = next(iter(site_dict.values()))
        claimed = site.name == 'Broken' or username == 'alice'
        status = MaigretCheckStatus.CLAIMED if claimed else MaigretCheckStatus.AVAILABLE
        return {
            site.name: {
                'status': MaigretCheckResult(username, site.name, '', status),
                'http_status': 200 if claimed else 404,
            }
        }

    # main() adjusts this named logger; restore it for subsequent tests.
    monkeypatch.setattr(logging.getLogger('maigret'), 'level', logging.NOTSET)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        'sys.argv',
        [
            'maigret',
            '--db',
            str(target),
            '--self-check',
            '--auto-disable',
            '--use-disabled-sites',
            '--no-autoupdate',
            '--no-progressbar',
            '--no-color',
        ],
    )
    with patch('maigret.checking.maigret', side_effect=result_for), patch(
        'builtins.input', return_value=answer
    ) as prompt:
        with pytest.raises(SystemExit) as exc:
            await cli.main()
        assert exc.value.code == 0
    prompt.assert_called_once_with('Do you want to save changes permanently? [Yn]\n')
    saved = json.loads(target.read_text(encoding='utf-8'))['sites']
    expected = (False, True) if answer == 'y' else (True, False)
    assert (
        tuple(saved[name].get('disabled', False) for name in ('Recovered', 'Broken'))
        == expected
    )
