"""Maigret checking logic test functions"""
import pytest
import asyncio
import logging
from maigret.executors import (
    AsyncioSimpleExecutor,
    AsyncioProgressbarExecutor,
    AsyncioProgressbarSemaphoreExecutor,
    AsyncioProgressbarQueueExecutor,
)

logger = logging.getLogger(__name__)


async def func(n):
    await asyncio.sleep(0.1 * (n % 3))
    return n


@pytest.mark.asyncio
async def test_simple_asyncio_executor():
    tasks = [(func, [n], {}) for n in range(10)]
    executor = AsyncioSimpleExecutor(logger=logger)
    assert await executor.run(tasks) == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert executor.execution_time > 0.2
    assert executor.execution_time < 0.3


@pytest.mark.asyncio
async def test_asyncio_progressbar_executor():
    tasks = [(func, [n], {}) for n in range(10)]

    executor = AsyncioProgressbarExecutor(logger=logger)
    # no guarantees for the results order
    assert sorted(await executor.run(tasks)) == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert executor.execution_time > 0.2
    assert executor.execution_time < 0.3


@pytest.mark.asyncio
async def test_asyncio_progressbar_semaphore_executor():
    tasks = [(func, [n], {}) for n in range(10)]

    executor = AsyncioProgressbarSemaphoreExecutor(logger=logger, in_parallel=5)
    # no guarantees for the results order
    assert sorted(await executor.run(tasks)) == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert executor.execution_time > 0.2
    assert executor.execution_time < 0.4


@pytest.mark.asyncio
async def test_asyncio_progressbar_queue_executor():
    tasks = [(func, [n], {}) for n in range(10)]

    executor = AsyncioProgressbarQueueExecutor(logger=logger, in_parallel=2)
    assert await executor.run(tasks) == [0, 1, 3, 2, 4, 6, 7, 5, 9, 8]
    assert executor.execution_time > 0.5
    assert executor.execution_time < 0.6

    executor = AsyncioProgressbarQueueExecutor(logger=logger, in_parallel=3)
    assert await executor.run(tasks) == [0, 3, 1, 4, 6, 2, 7, 9, 5, 8]
    assert executor.execution_time > 0.4
    assert executor.execution_time < 0.5

    executor = AsyncioProgressbarQueueExecutor(logger=logger, in_parallel=5)
    assert await executor.run(tasks) == [0, 3, 6, 1, 4, 7, 9, 2, 5, 8]
    assert executor.execution_time > 0.3
    assert executor.execution_time < 0.4

    executor = AsyncioProgressbarQueueExecutor(logger=logger, in_parallel=10)
    assert await executor.run(tasks) == [0, 3, 6, 9, 1, 4, 7, 2, 5, 8]
    assert executor.execution_time > 0.2
    assert executor.execution_time < 0.3
