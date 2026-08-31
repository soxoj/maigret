"""
Integration between REST API and core Maigret search logic.

Handles execution of searches, result collection, and job tracking.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime

from maigret.checking import maigret
from maigret.sites import MaigretDatabase
from maigret.result import MaigretCheckStatus

from .schemas import SearchResult, SearchStatus
from .job_manager import get_job_manager

logger = logging.getLogger(__name__)


class APIQueryNotify:
    """Notification handler that updates job status with search progress."""

    def __init__(self, job_id: str):
        """Initialize with job ID for tracking."""
        self.job_id = job_id
        self.job_manager = get_job_manager()
        self.total_sites = 0
        self.checked_count = 0
        self.results_dict = {}

    def set_total(self, total: int):
        """Set total number of sites to check."""
        self.total_sites = total
        self.job_manager.update_status(self.job_id, 'running', 0)

    def update(self, result, is_similar: bool = False):
        """
        Called for each site check completion.

        Converts Maigret result to API result format and stores it.
        """
        if not is_similar:
            self.checked_count += 1

        # Calculate progress
        progress = int((self.checked_count / self.total_sites * 100)) if self.total_sites > 0 else 0

        # Convert result to API format
        api_result = self._convert_result(result)

        if api_result:
            self.job_manager.add_result(self.job_id, api_result)

        # Update progress
        self.job_manager.update_status(self.job_id, 'running', progress)

        logger.debug(f"Job {self.job_id}: checked {self.checked_count}/{self.total_sites} sites")

    def _convert_result(self, result) -> Optional[SearchResult]:
        """Convert Maigret result to API SearchResult format."""
        try:
            status_map = {
                MaigretCheckStatus.CLAIMED: 'found',
                MaigretCheckStatus.NOT_CLAIMED: 'not_found',
                MaigretCheckStatus.ERROR: 'error',
                MaigretCheckStatus.UNKNOWN: 'unknown',
            }

            api_status = status_map.get(result.status, 'unknown')
            metadata = {}

            # Include extra information if available
            if result.ids_data:
                ids = {
                    k: v
                    for k, v in result.ids_data.items()
                    if k != '_extractor' and isinstance(v, (str, int, float))
                }
                metadata['ids'] = ids

            error_msg = None
            if result.status == MaigretCheckStatus.ERROR and result.errors:
                error_msg = str(result.errors[0]) if result.errors else None

            return SearchResult(
                site=result.site_name,
                username=result.username or '',
                url=result.site_url_user if result.status == MaigretCheckStatus.CLAIMED else None,
                status=api_status,
                error=error_msg,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Error converting result for {result.site_name}: {e}", exc_info=True)
            return None


async def execute_search(
    job_id: str,
    username: str,
    sites: Optional[List[str]] = None,
    timeout: Optional[int] = None,
    retries: Optional[int] = None,
) -> None:
    """
    Execute a Maigret search for the given job.

    Updates job status and results as the search progresses.
    This function is designed to be run in a separate event loop/thread.
    """
    job_manager = get_job_manager()

    try:
        logger.info(f"Starting search job {job_id} for username '{username}'")

        # Load sites database
        db = MaigretDatabase()
        if sites:
            # Filter to requested sites
            db.sites = {name: site for name, site in db.sites.items() if name in sites}

        # Create notification handler
        notify = APIQueryNotify(job_id)

        # Execute the search using the maigret function
        results = await maigret(
            username=username,
            site_dict=db.sites,
            logger=logger,
            query_notify=notify,
            timeout=timeout or 10,
            retries=retries or 1,
        )

        # Mark as completed
        job_manager.update_status(job_id, 'completed', 100)
        logger.info(f"Completed search job {job_id} with {len(results)} results")

    except asyncio.CancelledError:
        logger.info(f"Search job {job_id} was cancelled")
        job_manager.update_status(job_id, 'cancelled')

    except Exception as e:
        logger.error(f"Error executing search job {job_id}: {e}", exc_info=True)
        job_manager.set_error(job_id, str(e))


def start_search_job(
    job_id: str,
    username: str,
    sites: Optional[List[str]] = None,
    timeout: Optional[int] = None,
    retries: Optional[int] = None,
) -> None:
    """
    Start a search job in a background thread.

    This wraps the async search in a new event loop for thread execution.
    """
    def run_search():
        """Run search in a new event loop."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                execute_search(job_id, username, sites, timeout, retries)
            )
        finally:
            loop.close()

    # Start search in background thread
    import threading
    thread = threading.Thread(target=run_search, daemon=True, name=f"search-{job_id}")
    thread.start()
    logger.info(f"Started search thread for job {job_id}")
