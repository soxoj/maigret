#!/usr/bin/env python3
"""
Benchmark script to compare the performance of original Maigret with the modernized version.
"""

import asyncio
import time
import logging
import argparse
import os
import tracemalloc
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark")


async def benchmark_original(username, sites_count=100, timeout=10):
    """
    Benchmark the original Maigret implementation.
    
    Args:
        username: Username to check
        sites_count: Number of sites to check
        timeout: Request timeout
        
    Returns:
        Tuple of (results, execution_time, peak_memory)
    """
    from maigret.checking import maigret
    from maigret.sites import MaigretDatabase
    
    # Start memory tracking
    tracemalloc.start()
    
    # Load database
    db = MaigretDatabase()
    db_file = os.path.join("maigret", "resources", "data.json")
    db.load_from_json(db_file)
    
    # Get sites
    sites = db.ranked_sites_dict(sites_count)
    
    # Start timer
    start_time = time.time()
    
    # Run search
    results = await maigret(
        username=username,
        site_dict=sites,
        timeout=timeout,
        logger=logger
    )
    
    # Calculate time
    execution_time = time.time() - start_time
    
    # Get peak memory
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    return results, execution_time, peak / (1024 * 1024)  # Convert to MB


async def benchmark_modernized(username, sites_count=100, timeout=10):
    """
    Benchmark the modernized Maigret implementation.
    
    Args:
        username: Username to check
        sites_count: Number of sites to check
        timeout: Request timeout
        
    Returns:
        Tuple of (results, execution_time, peak_memory)
    """
    from maigret.modernized_maigret import search_for_username
    from maigret.sites import MaigretDatabase
    
    # Start memory tracking
    tracemalloc.start()
    
    # Load database
    db = MaigretDatabase()
    db_file = os.path.join("maigret", "resources", "data.json")
    db.load_from_json(db_file)
    
    # Get sites
    sites = db.ranked_sites_dict(sites_count)
    
    # Start timer
    start_time = time.time()
    
    # Run search
    results = await search_for_username(
        username=username,
        site_dict=sites,
        timeout=timeout,
        logger=logger
    )
    
    # Calculate time
    execution_time = time.time() - start_time
    
    # Get peak memory
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    return results, execution_time, peak / (1024 * 1024)  # Convert to MB


async def run_benchmark(usernames, sites_count=100, timeout=10):
    """
    Run the benchmark on multiple usernames.
    
    Args:
        usernames: List of usernames to check
        sites_count: Number of sites to check
        timeout: Request timeout
    """
    original_times = []
    modernized_times = []
    original_memory = []
    modernized_memory = []
    
    for username in usernames:
        logger.info(f"Benchmarking username: {username}")
        
        # Run original version
        logger.info("Running original implementation...")
        original_results, original_time, original_peak = await benchmark_original(
            username, 
            sites_count=sites_count,
            timeout=timeout
        )
        original_times.append(original_time)
        original_memory.append(original_peak)
        
        logger.info(f"Original time: {original_time:.2f}s, peak memory: {original_peak:.2f} MB")
        
        # Run modernized version
        logger.info("Running modernized implementation...")
        modernized_results, modernized_time, modernized_peak = await benchmark_modernized(
            username,
            sites_count=sites_count,
            timeout=timeout
        )
        modernized_times.append(modernized_time)
        modernized_memory.append(modernized_peak)
        
        logger.info(f"Modernized time: {modernized_time:.2f}s, peak memory: {modernized_peak:.2f} MB")
        
        # Calculate improvement
        time_improvement = ((original_time - modernized_time) / original_time) * 100
        memory_improvement = ((original_peak - modernized_peak) / original_peak) * 100
        logger.info(f"Performance improvement: {time_improvement:.2f}% faster, {memory_improvement:.2f}% less memory")
        
        # Compare result counts
        original_count = len([r for r in original_results.values() 
                            if r.get("status", {}).status == "CLAIMED"])
        
        modernized_count = 0
        for site_name, site_results in modernized_results.items():
            if site_name == "additional_usernames":
                continue
            
            status = site_results.get("status")
            if status and status.status.name == "CLAIMED":
                modernized_count += 1
        
        logger.info(f"Original found: {original_count} profiles")
        logger.info(f"Modernized found: {modernized_count} profiles")
        
        logger.info("-" * 50)
    
    # Overall statistics
    avg_original_time = sum(original_times) / len(original_times)
    avg_modernized_time = sum(modernized_times) / len(modernized_times)
    avg_original_memory = sum(original_memory) / len(original_memory)
    avg_modernized_memory = sum(modernized_memory) / len(modernized_memory)
    
    overall_time_improvement = ((avg_original_time - avg_modernized_time) / avg_original_time) * 100
    overall_memory_improvement = ((avg_original_memory - avg_modernized_memory) / avg_original_memory) * 100
    
    logger.info("=== BENCHMARK SUMMARY ===")
    logger.info(f"Number of usernames tested: {len(usernames)}")
    logger.info(f"Number of sites checked per username: {sites_count}")
    logger.info(f"Average time (original): {avg_original_time:.2f}s")
    logger.info(f"Average time (modernized): {avg_modernized_time:.2f}s")
    logger.info(f"Average memory (original): {avg_original_memory:.2f} MB")
    logger.info(f"Average memory (modernized): {avg_modernized_memory:.2f} MB")
    logger.info(f"Overall time improvement: {overall_time_improvement:.2f}%")
    logger.info(f"Overall memory improvement: {overall_memory_improvement:.2f}%")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Maigret performance benchmark")
    
    parser.add_argument(
        "usernames",
        nargs="+",
        help="Usernames to check in the benchmark"
    )
    
    parser.add_argument(
        "--sites",
        type=int,
        default=100,
        help="Number of sites to check (default: 100)"
    )
    
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Request timeout in seconds (default: 10.0)"
    )
    
    args = parser.parse_args()
    
    asyncio.run(run_benchmark(
        args.usernames,
        sites_count=args.sites,
        timeout=args.timeout
    ))