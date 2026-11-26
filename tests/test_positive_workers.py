"""Invalid concurrency must not silently return an empty successful scan."""

import asyncio
import logging
from typing import Callable, List, Tuple

import pytest

from maigret.executors import AsyncioQueueGeneratorExecutor


@pytest.mark.parametrize('workers', [0, -1, -10])
def test_executor_rejects_nonpositive_worker_count(workers):
    with pytest.raises(ValueError, match='greater than zero'):
        AsyncioQueueGeneratorExecutor(
            logger=logging.getLogger(__name__), in_parallel=workers
        )


@pytest.mark.parametrize('workers', [1, 2, 5])
@pytest.mark.asyncio
async def test_positive_worker_count_keeps_all_results(workers):
    async def result(value):
        await asyncio.sleep(0)
        return value

    executor = AsyncioQueueGeneratorExecutor(
        logger=logging.getLogger(__name__), in_parallel=workers
    )
    queries: List[Tuple[Callable, list, dict]] = [(result, [n], {}) for n in range(5)]
    results = [item async for item in executor.run(queries)]  # type: ignore[arg-type]
    assert sorted(results) == list(range(5))


@pytest.mark.parametrize('flag', ['-n', '--max-connections'])
@pytest.mark.parametrize('workers', ['0', '-1'])
@pytest.mark.asyncio
async def test_cli_rejects_invalid_concurrency_before_database_load(
    flag, workers, tmp_path, monkeypatch, capsys
):
    from maigret import maigret as cli

    monkeypatch.setattr(logging.getLogger('maigret'), 'level', logging.NOTSET)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('sys.argv', ['maigret', 'alice', flag, workers, '--no-color'])
    with pytest.raises(SystemExit) as exc:
        await cli.main()
    assert exc.value.code == 2
    output = capsys.readouterr()
    assert '--max-connections must be greater than zero' in output.err
    assert 'Using sites database:' not in output.out
    assert 'returned 0 accounts' not in output.out


@pytest.mark.parametrize('workers', [0, -2])
@pytest.mark.asyncio
async def test_cli_rejects_invalid_configured_concurrency(
    workers, tmp_path, monkeypatch, capsys
):
    from maigret import maigret as cli

    original_load = cli.Settings.load

    def load(settings):
        result = original_load(settings)
        settings.max_connections = workers
        return result

    monkeypatch.setattr(cli.Settings, 'load', load)
    monkeypatch.setattr(logging.getLogger('maigret'), 'level', logging.NOTSET)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('sys.argv', ['maigret', 'alice', '--no-color'])
    with pytest.raises(SystemExit) as exc:
        await cli.main()
    assert exc.value.code == 2
    assert '--max-connections must be greater than zero' in capsys.readouterr().err
