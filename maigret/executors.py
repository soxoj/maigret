import asyncio
import sys
import time
from typing import Any, Iterable, List, Callable

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
    # Deprecated: will be removed soon, don't use it
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
    # Deprecated: will be removed soon, don't use it
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
    # Deprecated: will be removed soon, don't use it
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
    # Deprecated: will be removed soon, don't use it
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
        # Pass a progress function; alive_bar by default
        self.progress_func = kwargs.get('progress_func', alive_bar)
        self.progress = None

    # TODO: tests
    async def increment_progress(self, count):
        """Update progress by calling the provided progress function."""
        if self.progress:
            if asyncio.iscoroutinefunction(self.progress):
                await self.progress(count)
            else:
                self.progress(count)
                await asyncio.sleep(0)

    # TODO: tests
    async def stop_progress(self):
        """Stop the progress tracking."""
        if hasattr(self.progress, "close") and self.progress:
            close_func = self.progress.close
            if asyncio.iscoroutinefunction(close_func):
                await close_func()
            else:
                close_func()
                await asyncio.sleep(0)

    async def worker(self):
        """Consume tasks from the queue and process them."""
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

            if self.progress:
                await self.increment_progress(1)

            self.queue.task_done()

    async def _run(self, queries: Iterable[QueryDraft]):
        """Main runner function to execute tasks with progress tracking."""
        self.results: List[Any] = []
        queries_list = list(queries)
        min_workers = min(len(queries_list), self.workers_count)
        workers = [create_task_func()(self.worker()) for _ in range(min_workers)]

        # Initialize the progress bar
        if self.progress_func:
            with self.progress_func(
                len(queries_list), title="Searching", force_tty=True
            ) as bar:
                self.progress = bar  # Assign alive_bar's callable to self.progress

                # Add tasks to the queue
                for t in queries_list:
                    await self.queue.put(t)

                # Wait for tasks to complete
                await self.queue.join()

                # Cancel any remaining workers
                for w in workers:
                    w.cancel()

        return self.results


class AsyncioQueueGeneratorExecutor:
    # Deprecated: will be removed soon, don't use it
    def __init__(self, *args, **kwargs):
        self.workers_count = kwargs.get('in_parallel', 10)
        self.queue = asyncio.Queue()
        self.timeout = kwargs.get('timeout')
        self.logger = kwargs['logger']
        self._results = asyncio.Queue()
        self._stop_signal = object()

    async def worker(self):
        """Process tasks from the queue and put results into the results queue."""
        while True:
            task = await self.queue.get()
            if task is self._stop_signal:
                self.queue.task_done()
                break

            try:
                f, args, kwargs = task
                query_future = f(*args, **kwargs)
                query_task = create_task_func()(query_future)

                try:
                    result = await asyncio.wait_for(query_task, timeout=self.timeout)
                except asyncio.TimeoutError:
                    result = kwargs.get('default')
                await self._results.put(result)
            except Exception as e:
                self.logger.error(f"Error in worker: {e}")
            finally:
                self.queue.task_done()

    async def run(self, queries: Iterable[Callable[..., Any]]):
        """Run workers to process queries in parallel."""
        start_time = time.time()

        # Add tasks to the queue
        for t in queries:
            await self.queue.put(t)

        # Create workers
        workers = [
            asyncio.create_task(self.worker()) for _ in range(self.workers_count)
        ]

        # Add stop signals
        for _ in range(self.workers_count):
            await self.queue.put(self._stop_signal)

        try:
            while any(w.done() is False for w in workers) or not self._results.empty():
                try:
                    result = await asyncio.wait_for(self._results.get(), timeout=1)
                    yield result
                except asyncio.TimeoutError:
                    pass
        finally:
            # Ensure all workers are awaited
            await asyncio.gather(*workers)
            self.execution_time = time.time() - start_time
            self.logger.debug(f"Spent time: {self.execution_time}")
