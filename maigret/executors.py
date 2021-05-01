import asyncio
import time
import tqdm
import sys
from typing import Iterable, Any, List

from .types import QueryDraft


def create_task_func():
    if sys.version_info.minor > 6:
        create_asyncio_task = asyncio.create_task
    else:
        loop = asyncio.get_event_loop()
        create_asyncio_task = loop.create_task
    return create_asyncio_task


class AsyncExecutor:
    def __init__(self, *args, **kwargs):
        self.logger = kwargs['logger']

    async def run(self, tasks: Iterable[QueryDraft]):
        start_time = time.time()
        results = await self._run(tasks)
        self.execution_time = time.time() - start_time
        self.logger.debug(f'Spent time: {self.execution_time}')
        return results

    async def _run(self, tasks: Iterable[QueryDraft]):
        await asyncio.sleep(0)


class AsyncioSimpleExecutor(AsyncExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def _run(self, tasks: Iterable[QueryDraft]):
        futures = [f(*args, **kwargs) for f, args, kwargs in tasks]
        return await asyncio.gather(*futures)


class AsyncioProgressbarExecutor(AsyncExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def _run(self, tasks: Iterable[QueryDraft]):
        futures = [f(*args, **kwargs) for f, args, kwargs in tasks]
        results = []
        for f in tqdm.asyncio.tqdm.as_completed(futures):
            results.append(await f)
        return results


class AsyncioProgressbarSemaphoreExecutor(AsyncExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.semaphore = asyncio.Semaphore(kwargs.get('in_parallel', 1))

    async def _run(self, tasks: Iterable[QueryDraft]):
        async def _wrap_query(q: QueryDraft):
            async with self.semaphore:
                f, args, kwargs = q
                return await f(*args, **kwargs)

        async def semaphore_gather(tasks: Iterable[QueryDraft]):
            coros = [_wrap_query(q) for q in tasks]
            results = []
            for f in tqdm.asyncio.tqdm.as_completed(coros):
                results.append(await f)
            return results

        return await semaphore_gather(tasks)


class AsyncioProgressbarQueueExecutor(AsyncExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workers_count = kwargs.get('in_parallel', 10)
        self.progress_func = kwargs.get('progress_func', tqdm.tqdm)
        self.queue = asyncio.Queue(self.workers_count)
        self.timeout = kwargs.get('timeout')

    async def worker(self):
        while True:
            try:
                f, args, kwargs = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                return

            query_future = f(*args, **kwargs)
            query_task = create_task_func()(query_future)
            try:
                result = await asyncio.wait_for(query_task, timeout=self.timeout)
            except asyncio.TimeoutError:
                result = kwargs.get('default')

            self.results.append(result)
            self.progress.update(1)
            self.queue.task_done()

    async def _run(self, queries: Iterable[QueryDraft]):
        self.results: List[Any] = []

        queries_list = list(queries)

        min_workers = min(len(queries_list), self.workers_count)

        workers = [create_task_func()(self.worker()) for _ in range(min_workers)]

        self.progress = self.progress_func(total=len(queries_list))
        for t in queries_list:
            await self.queue.put(t)
        await self.queue.join()
        for w in workers:
            w.cancel()
        self.progress.close()
        return self.results
