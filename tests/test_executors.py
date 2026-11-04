"""Maigret checking logic test functions"""

import pytest
import asyncio
import logging
import time
from typing import List, Tuple, Callable
from maigret.executors import AsyncioQueueGeneratorExecutor

logger = logging.getLogger(__name__)


async def func(n):
    await asyncio.sleep(0.1 * (n % 3))
    return n


async def slow_cleanup_func(n, cleanup_time, **kwargs):
    """Never finishes on its own; its cancellation cleanup is itself slow —
    simulates closing an HTTP session on a connection bot protection is
    holding open without completing. Accepts **kwargs the same way
    check_site_for_username does, since worker() calls f(*args, **kwargs)
    with the same dict it later reads 'default' out of."""
    try:
        await asyncio.sleep(100)
        return n
    finally:
        await asyncio.sleep(cleanup_time)


@pytest.mark.asyncio
async def test_asyncio_queue_generator_executor():
    tasks: List[Tuple[Callable, list, dict]] = [(func, [n], {}) for n in range(10)]

    executor = AsyncioQueueGeneratorExecutor(logger=logger, in_parallel=2)
    results = [result async for result in executor.run(tasks)]  # type: ignore[arg-type]
    assert results == [0, 1, 3, 2, 4, 6, 7, 5, 9, 8]
    assert executor.execution_time > 0.5
    assert executor.execution_time < 1.3

    executor = AsyncioQueueGeneratorExecutor(logger=logger, in_parallel=3)
    results = [result async for result in executor.run(tasks)]  # type: ignore[arg-type]
    assert results == [0, 3, 1, 4, 6, 2, 7, 9, 5, 8]
    assert executor.execution_time > 0.4
    assert executor.execution_time < 1.2

    executor = AsyncioQueueGeneratorExecutor(logger=logger, in_parallel=5)
    results = [result async for result in executor.run(tasks)]  # type: ignore[arg-type]
    assert results in (
        [0, 3, 6, 1, 4, 7, 9, 2, 5, 8],
        [0, 3, 6, 1, 4, 9, 7, 2, 5, 8],
    )
    assert executor.execution_time > 0.3
    assert executor.execution_time < 1.1

    executor = AsyncioQueueGeneratorExecutor(logger=logger, in_parallel=10)
    results = [result async for result in executor.run(tasks)]  # type: ignore[arg-type]
    assert results == [0, 3, 6, 9, 1, 4, 7, 2, 5, 8]
    assert executor.execution_time > 0.2
    assert executor.execution_time < 1.0


@pytest.mark.asyncio
async def test_worker_does_not_block_on_slow_cancellation_cleanup():
    """A task whose cancellation cleanup itself hangs (e.g. closing a
    session on a connection bot protection holds open without completing)
    must not make the worker wait past `timeout` for that cleanup to
    finish — see the asyncio.wait() vs wait_for() comment in worker()."""
    cleanup_time = 0.4
    per_task_timeout = 0.15
    tasks: List[Tuple[Callable, list, dict]] = [
        (slow_cleanup_func, [n, cleanup_time], {'default': f'default-{n}'})
        for n in range(3)
    ]

    executor = AsyncioQueueGeneratorExecutor(
        logger=logger, in_parallel=3, timeout=per_task_timeout
    )
    start = time.monotonic()
    results = [result async for result in executor.run(tasks)]  # type: ignore[arg-type]
    elapsed = time.monotonic() - start

    assert sorted(results) == ['default-0', 'default-1', 'default-2']
    # Must return close to per_task_timeout, not cleanup_time — a
    # wait_for()-based implementation blocks until cleanup_time instead.
    assert elapsed < cleanup_time

    # Let the orphaned cleanup tasks actually finish before the test's event
    # loop closes, so they don't leak past this test as pending-task warnings.
    await asyncio.sleep(cleanup_time)
