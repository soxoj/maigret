"""Maigret checking logic test functions"""

import pytest
import asyncio
import logging
from typing import List, Tuple, Callable
from maigret.executors import AsyncioQueueGeneratorExecutor

logger = logging.getLogger(__name__)


async def func(n):
    await asyncio.sleep(0.1 * (n % 3))
    return n


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
