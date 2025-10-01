#!/usr/bin/env python3
"""
Simple benchmark to compare original and modernized Maigret with a few specific sites.
"""

import asyncio
import time
import os
import sys
import json
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING)

# Add the repo directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Sites to check
SITES_TO_CHECK = ["Facebook", "Twitter", "Instagram", "LinkedIn", "YouTube"]

async def benchmark_original(username):
    """Benchmark the original Maigret implementation."""
    from maigret.checking import maigret
    from maigret.sites import MaigretDatabase
    import logging
    
    # Set up logger
    logger = logging.getLogger("maigret_original")
    logger.setLevel(logging.WARNING)
    
    # Load database
    db = MaigretDatabase()
    db_file = os.path.join("maigret", "resources", "data.json")
    with open(db_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
        db.load_from_json(json_data)
    
    # Get specific sites
    sites = {}
    db_sites = db.sites_dict
    for site_name in SITES_TO_CHECK:
        # Check for exact or case-insensitive match
        if site_name in db_sites:
            sites[site_name] = db_sites[site_name]
        else:
            # Try case-insensitive search
            for name, site in db_sites.items():
                if name.lower() == site_name.lower():
                    sites[name] = site
                    break
    
    # Start timer
    start_time = time.time()
    
    # Run search
    results = await maigret(
        username=username,
        site_dict=sites,
        timeout=10,
        logger=logger,
        no_progressbar=True,
    )
    
    # End timer
    execution_time = time.time() - start_time
    
    # Count results
    found_count = 0
    for site_result in results.values():
        status = site_result.get("status")
        if status and status.status == "CLAIMED":
            found_count += 1
    
    return execution_time, found_count

async def benchmark_modernized(username):
    """Benchmark the modernized Maigret implementation."""
    from maigret.modernized_maigret import search_for_username
    from maigret.sites import MaigretDatabase
    import logging
    
    # Set up logger
    logger = logging.getLogger("maigret_modernized")
    logger.setLevel(logging.WARNING)
    
    # Load database
    db = MaigretDatabase()
    db_file = os.path.join("maigret", "resources", "data.json")
    with open(db_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
        db.load_from_json(json_data)
    
    # Get specific sites
    sites = {}
    db_sites = db.sites_dict
    for site_name in SITES_TO_CHECK:
        # Check for exact or case-insensitive match
        if site_name in db_sites:
            sites[site_name] = db_sites[site_name]
        else:
            # Try case-insensitive search
            for name, site in db_sites.items():
                if name.lower() == site_name.lower():
                    sites[name] = site
                    break
    
    # Start timer
    start_time = time.time()
    
    # Run search
    results = await search_for_username(
        username=username,
        site_dict=sites,
        timeout=10,
        logger=logger,
    )
    
    # End timer
    execution_time = time.time() - start_time
    
    # Count results
    found_count = 0
    for site_name, site_results in results.items():
        if site_name == "additional_usernames":
            continue
            
        status = site_results.get("status")
        if status and status.status.name == "CLAIMED":
            found_count += 1
    
    return execution_time, found_count

async def main():
    username = "github"
    
    print(f"Running benchmark for username '{username}' on specific sites:")
    print(f"Sites: {', '.join(SITES_TO_CHECK)}")
    
    # Run original Maigret
    print("\nRunning original Maigret...")
    original_time, original_found = await benchmark_original(username)
    
    # Run modernized Maigret
    print("\nRunning modernized Maigret...")
    modernized_time, modernized_found = await benchmark_modernized(username)
    
    # Print results
    print("\n=== BENCHMARK RESULTS ===")
    print(f"Original Maigret: {original_time:.2f} seconds, found {original_found} profiles")
    print(f"Modernized Maigret: {modernized_time:.2f} seconds, found {modernized_found} profiles")
    
    # Calculate improvement
    improvement = (original_time - modernized_time) / original_time * 100
    print(f"\nPerformance improvement: {improvement:.2f}% faster")

if __name__ == "__main__":
    asyncio.run(main())