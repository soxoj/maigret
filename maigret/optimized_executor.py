"""
Optimized executor module for Maigret.
This module provides improved concurrency and task processing.
"""

import asyncio
import os
import time
import logging
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

from alive_progress import alive_bar

from .types import QueryDraft


class OptimizedExecutor:
    """
    An optimized task executor that efficiently processes multiple HTTP requests
    and other tasks with improved resource utilization.
    """
    
    def __init__(self, logger=None, in_parallel=None, timeout=10, progress_func=None):
        """
        Initialize the optimized executor.
        
        Args:
            logger: Logger instance
            in_parallel: Maximum number of concurrent tasks (auto-detected if None)
            timeout: Task timeout in seconds
            progress_func: Function for progress visualization
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Auto-detect optimal concurrency if not specified
        if in_parallel is None:
            # Use CPU count times 4 as a reasonable default for IO-bound operations
            # but cap at 64 to avoid overwhelming network resources
            in_parallel = min(64, os.cpu_count() * 4)
        
        self.workers_count = in_parallel
        self.timeout = timeout
        self.progress_func = progress_func or alive_bar
        self.execution_time = 0
        
        # Use a larger queue for buffering tasks
        self.queue = asyncio.Queue(in_parallel * 2)
        
        # Track active tasks and results
        self._active_tasks = set()
        self._results = []
        self._task_batches = {}
    
    def _create_task(self, coro):
        """Create an asyncio task with improved tracking."""
        task = asyncio.create_task(coro)
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)
        return task
    
    async def worker(self):
        """
        Improved worker that processes tasks from the queue with 
        better error handling and resource management.
        """
        while True:
            try:
                # Get the next task from the queue
                task_data = await self.queue.get()
                
                # Check for stop signal
                if task_data is None:
                    self.queue.task_done()
                    break
                
                # Extract task components
                task_id, task_fn, args, kwargs = task_data
                batch_key = kwargs.get('_batch_key')
                
                # Execute the task with timeout
                try:
                    future = task_fn(*args, **kwargs)
                    result = await asyncio.wait_for(future, timeout=self.timeout)
                except asyncio.TimeoutError:
                    self.logger.debug(f"Task {task_id} timed out")
                    result = kwargs.get('default')
                except Exception as e:
                    self.logger.error(f"Task {task_id} failed: {e}")
                    result = None
                
                # Store result
                self._results.append((task_id, result))
                
                # Update batch tracking if task is part of a batch
                if batch_key and batch_key in self._task_batches:
                    self._task_batches[batch_key].append((task_id, result))
                
                # Update progress
                if hasattr(self, 'progress') and self.progress:
                    if asyncio.iscoroutinefunction(self.progress):
                        await self.progress(1)
                    else:
                        self.progress(1)
                
                # Mark task as done
                self.queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Worker error: {e}")
                if not self.queue.empty():
                    self.queue.task_done()
    
    async def run(self, tasks: Iterable[QueryDraft]):
        """
        Run a collection of tasks with optimized concurrency.
        
        Args:
            tasks: Iterable of (function, args, kwargs) tuples
            
        Returns:
            List of results in task submission order
        """
        start_time = time.time()
        self._results = []
        
        # Convert tasks to list for processing
        tasks_list = list(tasks)
        if not tasks_list:
            return []
        
        # Determine optimal worker count based on task count
        worker_count = min(len(tasks_list), self.workers_count)
        
        # Create workers
        workers = [self._create_task(self.worker()) for _ in range(worker_count)]
        
        # Initialize progress tracking
        with self.progress_func(len(tasks_list), title="Processing", force_tty=True) as progress:
            self.progress = progress
            
            # Submit tasks to the queue with IDs for tracking
            for i, task_data in enumerate(tasks_list):
                fn, args, kwargs = task_data
                await self.queue.put((i, fn, args, kwargs))
            
            # Wait for all tasks to complete
            await self.queue.join()
            
            # Signal workers to stop
            for _ in range(worker_count):
                await self.queue.put(None)
            
            # Wait for all workers to finish
            await asyncio.gather(*workers)
        
        # Calculate execution time
        self.execution_time = time.time() - start_time
        self.logger.debug(f"Execution completed in {self.execution_time:.2f}s")
        
        # Sort results by task ID to maintain submission order
        sorted_results = [r for _, r in sorted(self._results, key=lambda x: x[0])]
        return sorted_results
    
    async def batch_run(self, task_batches: Dict[str, List[QueryDraft]]):
        """
        Run tasks in batches with tracking by batch key.
        
        Args:
            task_batches: Dictionary mapping batch keys to lists of tasks
            
        Returns:
            Dictionary mapping batch keys to lists of results
        """
        # Reset batch tracking
        self._task_batches = {key: [] for key in task_batches}
        
        # Flatten tasks with batch keys
        flat_tasks = []
        for batch_key, tasks in task_batches.items():
            for task in tasks:
                fn, args, kwargs = task
                kwargs = dict(kwargs)  # Create a copy to avoid modifying the original
                kwargs['_batch_key'] = batch_key  # Add batch key for tracking
                flat_tasks.append((fn, args, kwargs))
        
        # Run all tasks
        await self.run(flat_tasks)
        
        # Return results grouped by batch
        return {
            key: [result for _, result in sorted(batch_results, key=lambda x: x[0])]
            for key, batch_results in self._task_batches.items()
        }


class DynamicPriorityExecutor(OptimizedExecutor):
    """
    Enhanced executor that prioritizes tasks based on domain popularity,
    response time, and failure rates.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Track performance metrics by domain
        self.domain_stats = {}
        self.priority_queue = asyncio.PriorityQueue()
    
    def _extract_domain(self, url):
        """Extract domain from URL."""
        if not url or '://' not in url:
            return None
        
        try:
            domain = url.split('/')[2]
            return domain
        except:
            return None
    
    def _calculate_priority(self, task_data):
        """Calculate task priority based on domain statistics."""
        fn, args, kwargs = task_data
        
        # Extract URL from args or kwargs
        url = kwargs.get('url', None)
        if not url and args:
            # Try to find URL in positional args (common in HTTP checkers)
            for arg in args:
                if isinstance(arg, str) and ('://' in arg):
                    url = arg
                    break
        
        if not url:
            # Default priority if no URL is found
            return 50
        
        domain = self._extract_domain(url)
        if not domain:
            return 50
        
        # Get domain stats
        stats = self.domain_stats.get(domain, {})
        
        # Calculate priority (lower is higher priority)
        base_priority = 50
        
        # Penalize slow domains
        avg_time = stats.get('avg_time', 0.5)
        time_factor = min(50, int(avg_time * 20))
        
        # Penalize frequently failing domains
        error_rate = stats.get('error_rate', 0)
        error_factor = int(error_rate * 50)
        
        # Prioritize successful domains
        success_rate = stats.get('success_rate', 0.5)
        success_factor = int((1 - success_rate) * 30)
        
        # Calculate final priority (lower is higher priority)
        priority = base_priority + time_factor + error_factor + success_factor
        
        # Cap at reasonable values
        return max(1, min(100, priority))
    
    async def run(self, tasks: Iterable[QueryDraft]):
        """Run tasks with dynamic prioritization."""
        start_time = time.time()
        self._results = []
        
        # Prioritize tasks
        tasks_list = list(tasks)
        if not tasks_list:
            return []
        
        # Add tasks to priority queue
        for i, task_data in enumerate(tasks_list):
            priority = self._calculate_priority(task_data)
            await self.priority_queue.put((priority, (i, *task_data)))
        
        # Determine optimal worker count
        worker_count = min(len(tasks_list), self.workers_count)
        
        # Create workers that pull from priority queue instead of regular queue
        async def priority_worker():
            while not self.priority_queue.empty():
                _, (task_id, fn, args, kwargs) = await self.priority_queue.get()
                
                try:
                    # Execute task
                    task_start = time.time()
                    domain = self._extract_domain(kwargs.get('url', ''))
                    
                    try:
                        future = fn(*args, **kwargs)
                        result = await asyncio.wait_for(future, timeout=self.timeout)
                        success = True
                    except asyncio.TimeoutError:
                        self.logger.debug(f"Task {task_id} timed out")
                        result = kwargs.get('default')
                        success = False
                    except Exception as e:
                        self.logger.error(f"Task {task_id} failed: {e}")
                        result = None
                        success = False
                    
                    # Store result
                    self._results.append((task_id, result))
                    
                    # Update domain statistics
                    if domain:
                        stats = self.domain_stats.setdefault(domain, {
                            'count': 0,
                            'success_count': 0,
                            'error_count': 0,
                            'total_time': 0,
                        })
                        
                        task_time = time.time() - task_start
                        stats['count'] += 1
                        stats['total_time'] += task_time
                        
                        if success:
                            stats['success_count'] += 1
                        else:
                            stats['error_count'] += 1
                        
                        # Calculate averages
                        stats['avg_time'] = stats['total_time'] / stats['count']
                        stats['success_rate'] = stats['success_count'] / stats['count']
                        stats['error_rate'] = stats['error_count'] / stats['count']
                    
                    # Update progress
                    if hasattr(self, 'progress') and self.progress:
                        self.progress(1)
                
                except Exception as e:
                    self.logger.error(f"Worker error: {e}")
                
                finally:
                    self.priority_queue.task_done()
        
        # Initialize progress tracking
        with self.progress_func(len(tasks_list), title="Processing", force_tty=True) as progress:
            self.progress = progress
            
            # Start workers
            workers = [self._create_task(priority_worker()) for _ in range(worker_count)]
            
            # Wait for all tasks to complete
            await self.priority_queue.join()
            
            # Wait for all workers to finish
            await asyncio.gather(*workers)
        
        # Calculate execution time
        self.execution_time = time.time() - start_time
        self.logger.debug(f"Execution completed in {self.execution_time:.2f}s")
        
        # Sort results by task ID to maintain submission order
        sorted_results = [r for _, r in sorted(self._results, key=lambda x: x[0])]
        return sorted_results