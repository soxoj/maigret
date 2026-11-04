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

    def _log_late_task_result(self, task):
        """Done-callback for a task we stopped waiting on (timed out or the
        worker itself was cancelled). Nothing else will ever retrieve this
        task's outcome, so without this callback asyncio logs a noisy
        "exception was never retrieved" once it finally finishes unwinding.
        """
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            self.logger.debug(f"Timed-out/cancelled check task raised: {exc}")

    async def worker(self):
        """Process tasks from the queue and put results into the results queue."""
        while True:
            task = await self.queue.get()
            if task is self._stop_signal:
                self.queue.task_done()
                break

            query_task = None
            try:
                f, args, kwargs = task
                query_future = f(*args, **kwargs)
                query_task = asyncio.create_task(query_future)

                # Deliberately asyncio.wait(), not wait_for(): wait_for's
                # cancel-on-timeout path awaits the cancelled task's own
                # cleanup (e.g. closing an aiohttp/curl_cffi session) before
                # returning. A site that holds its connection open without
                # completing (bot protection doing exactly this) can make
                # that cleanup itself take far longer than `timeout`, which
                # blocks this worker — and the whole scan's progress — well
                # past the configured timeout. asyncio.wait() returns the
                # moment the deadline hits regardless of how long the task
                # takes to actually unwind; we let that happen in the
                # background instead of waiting on it here.
                done, _ = await asyncio.wait({query_task}, timeout=self.timeout)
                if query_task in done:
                    result = query_task.result()
                else:
                    query_task.cancel()
                    query_task.add_done_callback(self._log_late_task_result)
                    result = kwargs.get('default')
                await self._results.put(result)
            except asyncio.CancelledError:
                # The worker itself was cancelled (Ctrl+C / Stop button —
                # see run()'s finally). Request cancellation of whatever
                # query was in flight, but don't wait on it for the same
                # reason as above, then let the cancellation propagate so
                # this worker actually stops.
                if query_task is not None and not query_task.done():
                    query_task.cancel()
                    query_task.add_done_callback(self._log_late_task_result)
                raise
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
