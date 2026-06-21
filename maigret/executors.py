import asyncio
import time
from typing import Any, Iterable, Callable


class AsyncioQueueGeneratorExecutor:
    def __init__(self, *args, **kwargs):
        self.workers_count = kwargs.get('in_parallel', 10)
        self.queue: asyncio.Queue = asyncio.Queue()
        self.timeout = kwargs.get('timeout')
        self.logger = kwargs['logger']
        self._results: asyncio.Queue = asyncio.Queue()
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
                query_task = asyncio.create_task(query_future)

                try:
                    result = await asyncio.wait_for(query_task, timeout=self.timeout)
                except asyncio.TimeoutError:
                    result = kwargs.get('default')
                await self._results.put(result)
            except Exception as e:
                self.logger.error(f"Error in worker: {e}", exc_info=True)
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
            # If the consumer cancelled us (Ctrl+C → search_task.cancel()),
            # the workers are independent asyncio.Tasks that keep draining
            # the queue and blocking the finally — for ~timeout per item,
            # which is forever from the user's perspective. Cancel them
            # explicitly so this finally returns promptly. Swallow their
            # CancelledError via return_exceptions=True so it doesn't
            # re-raise here and mask the original cancellation.
            for w in workers:
                if not w.done():
                    w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
            self.execution_time = time.time() - start_time
            self.logger.debug(f"Spent time: {self.execution_time}")
