"""
Modernized Maigret module with performance improvements.
This module serves as an entry point for using the optimized Maigret components.
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Dict, List, Optional, Set, Tuple, Any, Union

# Import modernized components
from .modernized_checking import modernized_maigret
from .optimized_executor import OptimizedExecutor, DynamicPriorityExecutor
from .optimized_http import cleanup_resources
from .result import MaigretCheckResult, MaigretCheckStatus
from .sites import MaigretDatabase, MaigretSite


async def search_for_username(
    username: str,
    site_dict: Dict[str, MaigretSite] = None,
    db_file: str = None,
    logger: logging.Logger = None,
    timeout: float = 10,
    max_connections: int = 100,
    recursive_search: bool = False,
    proxy: str = None,
    tor_proxy: str = None,
    i2p_proxy: str = None,
    is_parsing_enabled: bool = True,
    *args, 
    **kwargs
) -> Dict[str, Any]:
    """
    Search for a username across multiple sites with improved performance.
    
    Args:
        username: Username to search for
        site_dict: Dictionary of sites to check (if None, loads from db_file)
        db_file: Path to JSON database file
        logger: Logger instance
        timeout: Request timeout in seconds
        max_connections: Maximum concurrent connections
        recursive_search: Whether to search recursively for related usernames
        proxy: HTTP proxy
        tor_proxy: Tor proxy
        i2p_proxy: I2P proxy
        is_parsing_enabled: Whether to parse profile pages
        
    Returns:
        Dictionary of results
    """
    # Set up logging if not provided
    if not logger:
        logger = logging.getLogger("maigret")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    # Load sites if not provided
    if not site_dict:
        if not db_file:
            # Use default data.json location
            current_dir = os.path.dirname(os.path.abspath(__file__))
            db_file = os.path.join(current_dir, "resources", "data.json")
        
        # Load site data
        logger.info(f"Loading site data from {db_file}")
        db = MaigretDatabase()
        
        # Load from file (not passing the file path directly)
        with open(db_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
            db.load_from_json(json_data)
        
        # Get top sites by default
        site_dict = db.ranked_sites_dict()
    
    start_time = time.time()
    
    # Create a clean copy of kwargs without sites_limit
    clean_kwargs = {k: v for k, v in kwargs.items() if k != 'sites_limit'}
    
    # Run the search
    results = await modernized_maigret(
        username=username,
        site_dict=site_dict,
        logger=logger,
        timeout=timeout,
        max_connections=max_connections,
        is_parsing_enabled=is_parsing_enabled,
        proxy=proxy,
        tor_proxy=tor_proxy,
        i2p_proxy=i2p_proxy,
        use_dynamic_executor=True,
        *args,
        **clean_kwargs
    )
    
    # Collect stats
    duration = time.time() - start_time
    
    # If recursive search is enabled
    if recursive_search and is_parsing_enabled:
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
            
            # Also get usernames from ids_usernames
            if "ids_usernames" in site_results:
                for new_username in site_results["ids_usernames"]:
                    if new_username != username:
                        new_usernames.add(new_username)
        
        # Search for new usernames if any found
        if new_usernames:
            logger.info(f"Found {len(new_usernames)} additional usernames to check")
            
            # Recursively search for each new username (limited to top sites)
            top_sites = {k: v for k, v in site_dict.items() if v.alexa_rank <= 10000}
            additional_results = {}
            
            for new_username in new_usernames:
                logger.info(f"Checking additional username: {new_username}")
                
                # Use same parameters but with smaller site set
                new_results = await modernized_maigret(
                    username=new_username,
                    site_dict=top_sites,
                    logger=logger,
                    timeout=timeout,
                    max_connections=max_connections,
                    is_parsing_enabled=False,  # Don't do recursive again
                    proxy=proxy,
                    tor_proxy=tor_proxy,
                    i2p_proxy=i2p_proxy,
                    *args,
                    **kwargs
                )
                
                # Add to additional results
                for site_name, site_result in new_results.items():
                    key = f"{new_username}@{site_name}"
                    site_result["derived_from"] = username
                    additional_results[key] = site_result
            
            # Add additional results to main results
            results["additional_usernames"] = additional_results
    
    # Clean up resources
    await cleanup_resources()
    
    # Log execution stats
    logger.info(f"Search completed in {duration:.2f} seconds")
    
    return results


async def search_multiple_usernames(
    usernames: List[str], 
    db_file: str = None,
    logger: logging.Logger = None,
    **kwargs
) -> Dict[str, Dict[str, Any]]:
    """
    Search for multiple usernames with optimized performance.
    
    Args:
        usernames: List of usernames to search for
        db_file: Path to JSON database file
        logger: Logger instance
        **kwargs: Additional arguments for search_for_username
        
    Returns:
        Dictionary mapping usernames to their search results
    """
    # Set up logging if not provided
    if not logger:
        logger = logging.getLogger("maigret")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    # Load site data once for all searches
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_file = db_file or os.path.join(current_dir, "resources", "data.json")
    
    logger.info(f"Loading site data from {db_file}")
    db = MaigretDatabase()
    
    # Load from file (not passing the file path directly)
    with open(db_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
        db.load_from_json(json_data)
    
    site_dict = db.ranked_sites_dict()
    
    # Store results for all usernames
    all_results = {}
    
    # Process each username
    for username in usernames:
        logger.info(f"Searching for username: {username}")
        
        # Get limited sites if specified
        sites_limit = kwargs.get('sites_limit', None)
        if sites_limit:
            limited_sites = {}
            count = 0
            for name, site in sorted(site_dict.items(), key=lambda x: x[1].alexa_rank or 999999):
                limited_sites[name] = site
                count += 1
                if count >= sites_limit:
                    break
            current_site_dict = limited_sites
        else:
            current_site_dict = site_dict
        
        results = await search_for_username(
            username=username,
            site_dict=current_site_dict,
            logger=logger,
            **kwargs
        )
        
        all_results[username] = results
    
    return all_results


async def main():
    """
    Main entry point for the modernized Maigret CLI.
    """
    import argparse
    
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Modernized Maigret - Fast OSINT username search tool"
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
    
    parser.add_argument(
        "--proxy",
        metavar="PROXY",
        help="Use proxy for HTTP requests (example: socks5://127.0.0.1:9050)",
    )
    
    parser.add_argument(
        "--sites",
        metavar="SITES",
        type=int,
        default=500,
        help="Number of sites to check (default: 500)",
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
    
    # Check for usernames
    if not args.username:
        parser.print_help()
        return
    
    # Process all usernames
    results = await search_multiple_usernames(
        usernames=args.username,
        db_file=args.db,
        logger=logger,
        recursive_search=args.recursive,
        timeout=args.timeout,
        max_connections=args.connections,
        proxy=args.proxy,
        sites_limit=args.sites,
    )
    
    # Display summary of results
    for username, user_results in results.items():
        claimed_count = 0
        available_count = 0
        unknown_count = 0
        
        for site_name, site_results in user_results.items():
            if site_name == "additional_usernames":
                continue
                
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
        
        # Print details for claimed sites
        logger.info("Profiles found:")
        for site_name, site_results in user_results.items():
            if site_name == "additional_usernames":
                continue
                
            status = site_results.get("status")
            if not status or status.status != MaigretCheckStatus.CLAIMED:
                continue
                
            url = status.site_url_user
            logger.info(f"  - {site_name}: {url}")
        
        # Print details for additional usernames if any
        if "additional_usernames" in user_results:
            additional = user_results["additional_usernames"]
            if additional:
                logger.info(f"Additional usernames found: {len(additional)}")
                
                # Group by username
                by_username = {}
                for key, results in additional.items():
                    username = key.split('@')[0]
                    if username not in by_username:
                        by_username[username] = []
                    
                    status = results.get("status")
                    if status and status.status == MaigretCheckStatus.CLAIMED:
                        by_username[username].append(
                            (status.site_name, status.site_url_user)
                        )
                
                # Print results by username
                for username, sites in by_username.items():
                    if sites:
                        logger.info(f"  - {username}: found on {len(sites)} sites")
                        for site_name, url in sites[:5]:  # Show top 5
                            logger.info(f"    - {site_name}: {url}")
                        
                        if len(sites) > 5:
                            logger.info(f"    - ... and {len(sites) - 5} more")


# Command-line entrypoint
def run():
    """Run the modernized Maigret tool."""
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())