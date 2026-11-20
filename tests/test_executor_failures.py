import asyncio
import logging
from typing import Any, cast
from unittest.mock import patch

import pytest

from maigret.checking import SimpleAiohttpChecker, maigret
from maigret.executors import AsyncioQueueGeneratorExecutor
from maigret.result import MaigretCheckStatus
from maigret.sites import MaigretSite


async def fail_query(**kwargs):
    raise OSError(24, 'Too many open files')


async def pass_query(**kwargs):
    return 'completed'


@pytest.mark.asyncio
async def test_failed_query_yields_default_and_worker_continues():
    executor = AsyncioQueueGeneratorExecutor(
        logger=logging.getLogger(__name__), in_parallel=1
    )
    queries: list[tuple] = [
        (fail_query, [], {'default': 'failed'}),
        (pass_query, [], {}),
    ]

    results = [result async for result in executor.run(cast(Any, queries))]

    assert results == ['failed', 'completed']
    assert executor.queue.empty()


@pytest.mark.asyncio
async def test_cancelled_query_does_not_yield_failure_default():
    started = asyncio.Event()

    async def wait_for_cancellation(**kwargs):
        started.set()
        await asyncio.Event().wait()

    executor = AsyncioQueueGeneratorExecutor(
        logger=logging.getLogger(__name__), in_parallel=1
    )
    results = []

    async def consume():
        async for result in executor.run(
            cast(Any, [(wait_for_cancellation, [], {'default': 'should-not-appear'})])
        ):
            results.append(result)

    consumer = asyncio.create_task(consume())
    await started.wait()
    consumer.cancel()
    with pytest.raises(asyncio.CancelledError):
        await consumer
    assert results == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'failure_stage, recovers', [('check', False), ('check', True), ('connector', False)]
)
async def test_checker_exception_retains_site_and_allows_retry(failure_stage, recovers):
    site = MaigretSite(
        'Example',
        {
            'urlMain': 'https://example.test',
            'url': 'https://example.test/{username}',
            'checkType': 'status_code',
        },
    )
    logger = logging.getLogger(__name__)
    side_effect = [
        OSError(24, 'Too many open files'),
        ('profile', 200, None) if recovers else OSError(24, 'Too many open files'),
    ]
    if failure_stage == 'connector':
        mocked_call = patch('maigret.checking.TCPConnector', side_effect=side_effect)
    else:
        mocked_call = patch.object(
            SimpleAiohttpChecker, 'check', side_effect=side_effect
        )
    with mocked_call as check:
        result = await maigret(
            'alice',
            {'Example': site},
            logger,
            retries=1,
            no_progressbar=True,
            timeout=0.1,
        )

    assert check.call_count == 2
    assert set(result) == {'Example'}
    expected = MaigretCheckStatus.CLAIMED if recovers else MaigretCheckStatus.UNKNOWN
    assert result['Example']['status'].status == expected
    if not recovers:
        assert result['Example']['status'].error.type == 'Request failed'


@pytest.mark.asyncio
@pytest.mark.parametrize('has_default', [False, True])
@pytest.mark.parametrize('default', [None, 'fallback'])
async def test_synchronous_failure_respects_optional_default(has_default, default):
    def fail_before_await(**kwargs):
        raise ValueError('invalid query setup')

    executor = AsyncioQueueGeneratorExecutor(
        logger=logging.getLogger(__name__), in_parallel=1
    )
    options = {'default': default} if has_default else {}
    results = [
        result
        async for result in executor.run(cast(Any, [(fail_before_await, [], options)]))
    ]
    assert results == ([default] if has_default else [])


@pytest.mark.asyncio
async def test_malformed_task_does_not_reuse_previous_default():
    executor = AsyncioQueueGeneratorExecutor(
        logger=logging.getLogger(__name__), in_parallel=1
    )
    queries: list[tuple] = [
        (fail_query, [], {'default': 'first-failure'}),
        ('malformed',),
        (pass_query, [], {}),
    ]

    results = [result async for result in executor.run(cast(Any, queries))]

    assert results == ['first-failure', 'completed']
    assert executor.queue.empty()
