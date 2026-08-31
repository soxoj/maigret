"""
Job management for async search operations.

Tracks search jobs, manages their lifecycle, and stores results.
"""

import uuid
import asyncio
import logging
from typing import Dict, Optional, Callable, Any, List
from datetime import datetime
from dataclasses import dataclass

from .schemas import SearchStatus, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class Job:
    """Represents a single search job."""
    job_id: str
    username: str
    status: SearchStatus
    task: Optional[asyncio.Task] = None
    event_loop: Optional[asyncio.AbstractEventLoop] = None

    def __hash__(self):
        return hash(self.job_id)

    def __eq__(self, other):
        return isinstance(other, Job) and self.job_id == other.job_id


class JobManager:
    """Manages search jobs with lifecycle tracking."""

    def __init__(self, max_jobs: int = 1000):
        """Initialize the job manager."""
        self.jobs: Dict[str, Job] = {}
        self.max_jobs = max_jobs
        self.logger = logger

    def create_job(self, username: str) -> str:
        """Create a new search job and return its ID."""
        if len(self.jobs) >= self.max_jobs:
            self.logger.warning(f"Job limit ({self.max_jobs}) reached, removing oldest job")
            # Remove oldest job by ID (simple FIFO)
            oldest_id = next(iter(self.jobs))
            del self.jobs[oldest_id]

        job_id = str(uuid.uuid4())
        status = SearchStatus(
            job_id=job_id,
            username=username,
            status='pending',
        )
        job = Job(job_id=job_id, username=username, status=status)
        self.jobs[job_id] = job
        self.logger.info(f"Created job {job_id} for username '{username}'")
        return job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return self.jobs.get(job_id)

    def get_status(self, job_id: str) -> Optional[SearchStatus]:
        """Get the status of a job."""
        job = self.get_job(job_id)
        return job.status if job else None

    def update_status(self, job_id: str, status: str, progress: int = None) -> bool:
        """Update job status."""
        job = self.get_job(job_id)
        if not job:
            return False

        job.status.status = status
        if progress is not None:
            job.status.progress = max(0, min(100, progress))

        if status == 'running' and not job.status.started_at:
            job.status.started_at = datetime.utcnow()
        elif status in ('completed', 'failed', 'cancelled') and not job.status.completed_at:
            job.status.completed_at = datetime.utcnow()

        return True

    def add_result(self, job_id: str, result: SearchResult) -> bool:
        """Add a search result to a job."""
        job = self.get_job(job_id)
        if not job:
            return False

        job.status.results.append(result)
        job.status.results_count = len(job.status.results)
        return True

    def set_error(self, job_id: str, error: str) -> bool:
        """Set error message for a job."""
        job = self.get_job(job_id)
        if not job:
            return False

        job.status.error = error
        job.status.status = 'failed'
        job.status.completed_at = datetime.utcnow()
        return True

    def get_results(self, job_id: str) -> Optional[List[SearchResult]]:
        """Get results for a completed job."""
        job = self.get_job(job_id)
        return job.status.results if job else None

    def set_task(self, job_id: str, task: asyncio.Task, loop: asyncio.AbstractEventLoop) -> bool:
        """Associate an async task with a job."""
        job = self.get_job(job_id)
        if not job:
            return False

        job.task = task
        job.event_loop = loop
        return True

    def get_task(self, job_id: str) -> Optional[asyncio.Task]:
        """Get the async task for a job."""
        job = self.get_job(job_id)
        return job.task if job else None

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        job = self.get_job(job_id)
        if not job:
            return False

        if job.task and not job.task.done():
            job.task.cancel()
            job.status.status = 'cancelled'
            job.status.completed_at = datetime.utcnow()
            self.logger.info(f"Cancelled job {job_id}")
            return True

        return False

    def cleanup_job(self, job_id: str) -> bool:
        """Remove a job from tracking (for cleanup after retention period)."""
        if job_id in self.jobs:
            del self.jobs[job_id]
            self.logger.info(f"Cleaned up job {job_id}")
            return True
        return False


# Global job manager instance
_job_manager = JobManager()


def get_job_manager() -> JobManager:
    """Get the global job manager instance."""
    return _job_manager
