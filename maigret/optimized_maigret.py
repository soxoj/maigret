"""
Optimized main module for Maigret.
This module integrates all the optimization improvements.
"""

import asyncio
import logging
import os
import sys
import time
from typing import Dict, List, Optional, Set, Tuple, Any

from .optimized_checker import OptimizedHttpChecker, OptimizedChecker, OptimizedDomainResolver
from .optimized_executor import OptimizedExecutor, DynamicPriorityExecutor
from .optimized_sites import OptimizedMaigretSite, LazyMaigretDatabase
from .result import MaigretCheckResult, MaigretCheckStatus


async def check_username_on_sites(username, sites, logger=None, timeout=10, max_connections=50):
    """
    Check a username across multiple sites with optimized performance.
    
    Args:
        username: Username to check
        sites: List of site objects to check
        logger: Logger instance
        timeout: Request timeout in seconds
        max_connections: Maximum concurrent connections
        
    Returns:
        Dictionary of site results
    """
    if not logger:
        logger = logging.getLogger("maigret")
    
    # Create results container
    results = {}
    
    # Group sites by domain for connection pooling
    domain_groups = {}
    for site in sites:
        if not site.url_main:
            continue
            
        domain = site.url_main.split('/')[2] if '://' in site.url_main else site.url_main
        if domain not in domain_groups:
            domain_groups[domain] = []
        domain_groups[domain].append(site)
    
    # Create optimized executor with dynamic prioritization
    executor = DynamicPriorityExecutor(
        logger=logger,
        in_parallel=max_connections,
        timeout=timeout
    )
    
    # Create task batches
    async def check_site(site):
        """Function to check a single site."""
        site_results = {}
        
        try:
            # Prepare URL and headers
            url = site.url.format(username=username)
            headers = site.headers.copy() if site.headers else {}
            
            # Add random user agent if not specified
            if "User-Agent" not in headers:
                from .utils import get_random_user_agent
                headers["User-Agent"] = get_random_user_agent()
            
            # Create optimized checker
            checker = OptimizedHttpChecker(logger=logger)
            method = "head" if site.request_head_only else "get"
            checker.prepare(url, headers=headers, timeout=timeout, method=method)
            
            # Perform check
            html_text, status_code, check_error = await checker.check()
            
            # Process result
            status = None
            
            if check_error:
                status = MaigretCheckStatus.UNKNOWN
            else:
                # Check for presence/absence indicators
                is_present = False
                is_absent = False
                
                if html_text:
                    # Check presence indicators
                    if not site.presense_strs:
                        is_present = True
                    else:
                        for flag in site.presense_strs:
                            if flag in html_text:
                                is_present = True
                                break
                    
                    # Check absence indicators
                    if site.absence_strs:
                        for flag in site.absence_strs:
                            if flag in html_text:
                                is_absent = True
                                break
                
                # Determine status based on site check type
                check_type = site.check_type
                
                if check_type == "message":
                    if is_present and not is_absent:
                        status = MaigretCheckStatus.CLAIMED
                    else:
                        status = MaigretCheckStatus.AVAILABLE
                elif check_type == "status_code":
                    if 200 <= status_code < 300:
                        status = MaigretCheckStatus.CLAIMED
                    else:
                        status = MaigretCheckStatus.AVAILABLE
                elif check_type == "response_url":
                    if 200 <= status_code < 300 and is_present:
                        status = MaigretCheckStatus.CLAIMED
                    else:
                        status = MaigretCheckStatus.AVAILABLE
                else:
                    # Default to unknown if check type is not recognized
                    status = MaigretCheckStatus.UNKNOWN
            
            # Create result object
            result = MaigretCheckResult(
                username=username,
                site_name=site.name,
                site_url_user=url,
                status=status or MaigretCheckStatus.UNKNOWN,
                query_time=None,  # We're not tracking this yet
                tags=site.tags,
                error=check_error,
            )
            
            # Extract additional data if available
            if status == MaigretCheckStatus.CLAIMED and html_text:
                from socid_extractor import extract
                try:
                    extracted_ids = extract(html_text)
                    if extracted_ids:
                        result.ids_data = extracted_ids
                except Exception as e:
                    logger.debug(f"Data extraction error for {site.name}: {e}")
            
            site_results["status"] = result
            site_results["http_status"] = status_code
            
        except Exception as e:
            logger.error(f"Error checking {site.name}: {e}")
            site_results["status"] = MaigretCheckResult(
                username=username,
                site_name=site.name,
                site_url_user=site.url.format(username=username) if site.url else "",
                status=MaigretCheckStatus.UNKNOWN,
                query_time=None,
                tags=site.tags,
                error=str(e),
            )
        
        return site.name, site_results
    
    # Create tasks for each domain group
    all_tasks = []
    for domain, domain_sites in domain_groups.items():
        for site in domain_sites:
            all_tasks.append((check_site, (site,), {}))
    
    # Execute all tasks
    logger.info(f"Checking {username} on {len(all_tasks)} sites...")
    start_time = time.time()
    
    # Execute tasks
    raw_results = await executor.run(all_tasks)
    
    # Process results
    for result in raw_results:
        if result:
            site_name, site_results = result
            results[site_name] = site_results
    
    # Report execution stats
    duration = time.time() - start_time
    logger.info(f"Completed checking {username} in {duration:.2f} seconds")
    
    # Clean up resources
    await OptimizedChecker.cleanup()
    
    return results


async def maigret(username, sites_data=None, db_file=None, logger=None, recursive_search=False,
                 timeout=10, max_connections=50):
    """
    Main Maigret search function with optimized performance.
    
    Args:
        username: Username to check
        sites_data: Optional pre-loaded sites data
        db_file: Path to JSON database file
        logger: Logger instance
        recursive_search: Whether to search recursively for related usernames
        timeout: Request timeout in seconds
        max_connections: Maximum concurrent connections
        
    Returns:
        Dictionary of results
    """
    # Set up logging
    if not logger:
        logger = logging.getLogger("maigret")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    # Get site database
    if sites_data:
        db = sites_data
    else:
        # Use lazy loading to get database instance
        db = LazyMaigretDatabase.get_instance(db_file)
    
    # Get sites to check (top 500 by default)
    sites = db.get_popular_sites(500)
    logger.info(f"Loaded {len(sites)} sites to check")
    
    # Check username across sites
    results = await check_username_on_sites(
        username, 
        sites, 
        logger=logger,
        timeout=timeout,
        max_connections=max_connections
    )
    
    # Process for recursive search if enabled
    if recursive_search:
        # Extract new usernames from results
        new_usernames = set()
        
        for site_name, site_results in results.items():
            result = site_results.get("status")
            if not result or result.status != MaigretCheckStatus.CLAIMED:
                continue
                
            # Extract usernames from ids_data
            if hasattr(result, "ids_data") and result.ids_data:
                for key, value in result.ids_data.items():
                    if "username" in key.lower() and value != username:
                        new_usernames.add(value)
        
        # Search for new usernames
        if new_usernames:
            logger.info(f"Found {len(new_usernames)} additional usernames to check")
            
            # Recursively search for each new username
            for new_username in new_usernames:
                logger.info(f"Checking additional username: {new_username}")
                new_results = await check_username_on_sites(
                    new_username,
                    sites[:100],  # Only check top 100 sites for additional usernames
                    logger=logger,
                    timeout=timeout,
                    max_connections=max_connections
                )
                
                # Add to results with special flag
                for site_name, site_result in new_results.items():
                    if site_name not in results:
                        site_result["is_additional"] = True
                        results[site_name] = site_result
        
    return results


async def main():
    """
    Main entry point for the optimized Maigret tool.
    """
    import argparse
    import os
    
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Optimized Maigret - OSINT username search tool"
    )
    
    parser.add_argument(
        "username",
        nargs="*",
        metavar="USERNAMES",
        help="One or more usernames to search for",
    )
    
    parser.add_argument(
        "--timeout",
        metavar="TIMEOUT",
        type=float,
        default=10.0,
        help="Time in seconds to wait for response (default: 10)",
    )
    
    parser.add_argument(
        "-c",
        "--connections",
        metavar="CONNECTIONS",
        type=int,
        default=50,
        help="Maximum number of concurrent connections (default: 50)",
    )
    
    parser.add_argument(
        "--recursive",
        action="store_true",
        default=False,
        help="Enable recursive search for additional usernames",
    )
    
    parser.add_argument(
        "--db",
        metavar="DB_FILE",
        help="Path to data.json file (default: built-in)",
    )
    
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose output",
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Set up logging
    logger = logging.getLogger("maigret")
    logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Determine database file
    db_file = args.db
    if not db_file:
        # Find built-in data.json
        current_dir = os.path.dirname(os.path.abspath(__file__))
        db_file = os.path.join(current_dir, "resources", "data.json")
    
    # Check for usernames
    if not args.username:
        parser.print_help()
        return
    
    # Process each username
    for username in args.username:
        logger.info(f"Searching for username: {username}")
        
        # Run the search
        results = await maigret(
            username,
            db_file=db_file,
            logger=logger,
            recursive_search=args.recursive,
            timeout=args.timeout,
            max_connections=args.connections
        )
        
        # Process and display results
        claimed_count = 0
        available_count = 0
        unknown_count = 0
        
        for site_name, site_results in results.items():
            status = site_results.get("status")
            if not status:
                continue
                
            if status.status == MaigretCheckStatus.CLAIMED:
                claimed_count += 1
            elif status.status == MaigretCheckStatus.AVAILABLE:
                available_count += 1
            else:
                unknown_count += 1
        
        logger.info(f"Results for {username}:")
        logger.info(f"  - Found: {claimed_count}")
        logger.info(f"  - Available: {available_count}")
        logger.info(f"  - Unknown/Error: {unknown_count}")
        
        # Print detailed results for claimed sites
        logger.info("Profiles found:")
        for site_name, site_results in results.items():
            status = site_results.get("status")
            if not status or status.status != MaigretCheckStatus.CLAIMED:
                continue
                
            url = status.site_url_user
            logger.info(f"  - {site_name}: {url}")
    
    # Clean up resources
    await OptimizedChecker.cleanup()


# Command-line entrypoint
def run():
    """Run the optimized Maigret tool."""
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())