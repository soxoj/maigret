#!/usr/bin/env python3
"""
Simple benchmark script to compare the performance of original vs. modernized Maigret.
"""

import asyncio
import time
import os
import sys

# Add the repo directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def run_original(username, sites_count=20):
    """Run the original version of Maigret."""
    from maigret.checking import maigret
    from maigret.sites import MaigretDatabase
    import logging
    
    # Set up logger
    logger = logging.getLogger("maigret_original")
    logger.setLevel(logging.WARNING)  # Minimize output
    
    # Set up database
    db = MaigretDatabase()
    db_file = os.path.join("maigret", "resources", "data.json")
    with open(db_file, 'r', encoding='utf-8') as f:
        import json
        json_data = json.load(f)
        db.load_from_json(json_data)
    
    # Get limited site dict
    sites = db.ranked_sites_dict(sites_count)
    
    # Measure execution time
    start_time = time.time()
    
    # Run the search
    results = await maigret(
        username=username,
        site_dict=sites,
        timeout=10,
        logger=logger,
        no_progressbar=True,
    )
    
    # Calculate execution time
    end_time = time.time()
    duration = end_time - start_time
    
    # Count found profiles
    found_count = sum(1 for r in results.values() 
                    if r.get("status", {}).status == "CLAIMED")
    
    return {
        'duration': duration,
        'found_count': found_count,
    }


async def run_modernized(username, sites_count=20):
    """Run the modernized version of Maigret."""
    from maigret.modernized_maigret import search_for_username
    from maigret.sites import MaigretDatabase
    import logging
    
    # Set up logger
    logger = logging.getLogger("maigret_modernized")
    logger.setLevel(logging.WARNING)  # Minimize output
    
    # Set up database
    db = MaigretDatabase()
    db_file = os.path.join("maigret", "resources", "data.json")
    with open(db_file, 'r', encoding='utf-8') as f:
        import json
        json_data = json.load(f)
        db.load_from_json(json_data)
    
    # Get limited site dict
    sites = db.ranked_sites_dict(sites_count)
    
    # Measure execution time
    start_time = time.time()
    
    # Run the search
    results = await search_for_username(
        username=username,
        site_dict=sites,
        timeout=10,
        logger=logger,
    )
    
    # Calculate execution time
    end_time = time.time()
    duration = end_time - start_time
    
    # Count found profiles
    found_count = 0
    for site_name, site_results in results.items():
        if site_name == "additional_usernames":
            continue
        
        status = site_results.get("status")
        if status and status.status.name == "CLAIMED":
            found_count += 1
    
    return {
        'duration': duration,
        'found_count': found_count,
    }


async def main():
    """Run the benchmark and display results."""
    username = "github"
    sites_count = 10  # Use a very small number to avoid timeouts
    
    print(f"Running benchmark for username '{username}' on {sites_count} sites...")
    
    # Run original version
    print("\nRunning original Maigret...")
    original_results = await run_original(username, sites_count)
    
    # Run modernized version
    print("\nRunning modernized Maigret...")
    modernized_results = await run_modernized(username, sites_count)
    
    # Display results
    print("\n=== BENCHMARK RESULTS ===")
    print(f"Original Maigret execution time: {original_results['duration']:.2f} seconds")
    print(f"Original Maigret profiles found: {original_results['found_count']}")
    print(f"Modernized Maigret execution time: {modernized_results['duration']:.2f} seconds")
    print(f"Modernized Maigret profiles found: {modernized_results['found_count']}")
    
    # Calculate performance improvement
    speedup = (original_results['duration'] - modernized_results['duration']) / original_results['duration'] * 100
    print(f"\nPerformance improvement: {speedup:.2f}% faster")


if __name__ == "__main__":
    asyncio.run(main())