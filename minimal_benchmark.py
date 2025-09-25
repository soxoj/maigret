#!/usr/bin/env python3
"""
Minimal benchmark script to compare the performance of original vs. modernized Maigret
using a small, predefined list of sites.
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

# Predefined sites to check (popular, reliable sites)
SITES_TO_CHECK = [
    "Facebook",
    "GitHub",
    "Twitter",
    "Instagram",
    "YouTube",
    "LinkedIn",
]

async def run_original(username):
    """Run the original version of Maigret with predefined sites."""
    from maigret.checking import maigret
    from maigret.sites import MaigretDatabase, MaigretSite
    
    # Set up logger
    logger = logging.getLogger("maigret_original")
    logger.setLevel(logging.WARNING)
    
    # Load full site database
    db = MaigretDatabase()
    db_file = os.path.join("maigret", "resources", "data.json")
    with open(db_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
        db.load_from_json(json_data)
    
    # Create a dictionary with just our predefined sites
    sites = {}
    for site_name in SITES_TO_CHECK:
        for name, site in db.sites.items():
            if name.lower() == site_name.lower():
                sites[name] = site
                break
    
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

async def run_modernized(username):
    """Run the modernized version of Maigret with predefined sites."""
    from maigret.modernized_maigret import search_for_username
    from maigret.sites import MaigretDatabase
    
    # Set up logger
    logger = logging.getLogger("maigret_modernized")
    logger.setLevel(logging.WARNING)
    
    # Load full site database
    db = MaigretDatabase()
    db_file = os.path.join("maigret", "resources", "data.json")
    with open(db_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
        db.load_from_json(json_data)
    
    # Create a dictionary with just our predefined sites
    sites = {}
    for site_name in SITES_TO_CHECK:
        for name, site in db.sites.items():
            if name.lower() == site_name.lower():
                sites[name] = site
                break
    
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
    
    print(f"Running benchmark for username '{username}' on {len(SITES_TO_CHECK)} predefined sites...")
    print(f"Sites: {', '.join(SITES_TO_CHECK)}")
    
    # Run original version
    print("\nRunning original Maigret...")
    original_results = await run_original(username)
    
    # Run modernized version
    print("\nRunning modernized Maigret...")
    modernized_results = await run_modernized(username)
    
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