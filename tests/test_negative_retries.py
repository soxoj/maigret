"""Invalid negative retry budgets must never start or repeat requests."""

import logging
from unittest.mock import Mock

import pytest

from maigret import checking
from maigret.errors import CheckError
from maigret.result import MaigretCheckResult, MaigretCheckStatus
from maigret.sites import MaigretSite


@pytest.mark.parametrize('retries', [-1, -2, -10])
@pytest.mark.asyncio
async def test_api_rejects_negative_retries(retries):
    notify = Mock()
    with pytest.raises(ValueError, match='zero or greater'):
        await checking.maigret(
            'alice',
            {},
            logging.getLogger(__name__),
            retries=retries,
            query_notify=notify,
        )
    notify.start.assert_not_called()


@pytest.mark.parametrize('retries', [-1, -2])
@pytest.mark.parametrize('configured', [False, True])
@pytest.mark.asyncio
async def test_cli_rejects_negative_retry_budget(
    retries, configured, tmp_path, monkeypatch, capsys
):
    from maigret import db_updater
    from maigret import maigret as cli

    def unexpected_database_load(*args, **kwargs):
        pytest.fail('invalid retry budget reached database resolution')

    monkeypatch.setattr(db_updater, 'resolve_db_path', unexpected_database_load)
    monkeypatch.setattr(logging.getLogger('maigret'), 'level', logging.NOTSET)
    monkeypatch.chdir(tmp_path)
    if configured:
        original_load = cli.Settings.load

        def load(settings):
            result = original_load(settings)
            settings.retries_count = retries
            return result

        monkeypatch.setattr(cli.Settings, 'load', load)
        argv = ['maigret', 'alice']
    else:
        argv = ['maigret', 'alice', '--retries', str(retries)]
    monkeypatch.setattr('sys.argv', argv)
    with pytest.raises(SystemExit) as exc:
        await cli.main()
    assert exc.value.code == 2
    assert '--retries must be zero or greater' in capsys.readouterr().err


@pytest.mark.parametrize('retries', [0, 1, 2])
@pytest.mark.asyncio
async def test_nonnegative_retry_budget_retains_attempt_count(retries, monkeypatch):
    site = MaigretSite(
        'Local',
        {
            'urlMain': 'https://example.test',
            'url': 'https://example.test/{username}',
            'checkType': 'status_code',
        },
    )
    calls = []

    async def temporary_failure(site, username, options, logger, notify, **kwargs):
        calls.append(kwargs['retry'])
        return site.name, {
            'site': site,
            'status': MaigretCheckResult(
                username,
                site.name,
                '',
                MaigretCheckStatus.UNKNOWN,
                error=CheckError('Request timeout'),
            ),
        }

    monkeypatch.setattr(checking, 'check_site_for_username', temporary_failure)
    results = await checking.maigret(
        'alice',
        {'Local': site},
        logging.getLogger(__name__),
        retries=retries,
        no_progressbar=True,
        dns_resolver='threaded',
    )
    assert list(results) == ['Local']
    assert calls == list(range(retries + 1))
