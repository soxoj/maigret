import asyncio
import sys
import time
from typing import Any, Iterable, List

import alive_progress
from alive_progress import alive_bar

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
        self.semaphore = asyncio.Semaphore(kwargs.get('in_parallel', 100))

    async def _run(self, tasks: Iterable[QueryDraft]):
        async def sem_task(f, args, kwargs):
            async with self.semaphore:
                return await f(*args, **kwargs)

        futures = [sem_task(f, args, kwargs) for f, args, kwargs in tasks]
        return await asyncio.gather(*futures)


class AsyncioProgressbarExecutor(AsyncExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def _run(self, tasks: Iterable[QueryDraft]):
        futures = [f(*args, **kwargs) for f, args, kwargs in tasks]
        total_tasks = len(futures)
        results = []

        # Use alive_bar for progress tracking
        with alive_bar(total_tasks, title='Searching', force_tty=True) as progress:
            # Chunk progress updates for efficiency
            async def track_task(task):
                result = await task
                progress()  # Update progress bar once task completes
                return result

            # Use gather to run tasks concurrently and track progress
            results = await asyncio.gather(*(track_task(f) for f in futures))

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

            # Use alive_bar correctly as a context manager
            with alive_bar(len(coros), title='Searching', force_tty=True) as progress:
                for f in asyncio.as_completed(coros):
                    results.append(await f)
                    progress()  # Update the progress bar
            return results

        return await semaphore_gather(tasks)


class AsyncioProgressbarQueueExecutor(AsyncExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workers_count = kwargs.get('in_parallel', 10)
        self.queue = asyncio.Queue(self.workers_count)
        self.timeout = kwargs.get('timeout')
        # a function to show updated progress, alive_bar by default
        self.progress_func = kwargs.get('progress_func', None)

    async def increment_progress(self, count):
        update_func = self.progress.update
        if asyncio.iscoroutinefunction(update_func):
            await update_func(count)
        else:
            update_func(count)
        await asyncio.sleep(0)

    async def stop_progress(self):
        stop_func = self.progress.close
        if asyncio.iscoroutinefunction(stop_func):
            await stop_func()
        else:
            stop_func()
        await asyncio.sleep(0)

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
            await self.increment_progress(1)
            self.queue.task_done()

    async def _run(self, queries: Iterable[QueryDraft]):
        self.results: List[Any] = []
        queries_list = list(queries)
        min_workers = min(len(queries_list), self.workers_count)

        workers = [create_task_func()(self.worker()) for _ in range(min_workers)]

        if self.progress_func:
            self.progress = self.progress_func(total=len(queries_list))

            for t in queries_list:
                await self.queue.put(t)

            await self.queue.join()

            for w in workers:
                w.cancel()

            await self.stop_progress()
        else:
            # Initialize alive_progress bar
            with alive_bar(len(queries_list), title="Searching", force_tty=True) as bar:
                self.update = bar  # `alive_bar` uses its instance to update progress

                for t in queries_list:
                    await self.queue.put(t)

                await self.queue.join()

                for w in workers:
                    w.cancel()

        return self.results