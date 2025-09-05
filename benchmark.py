#!/usr/bin/env python3
"""
Simple benchmark to compare original Maigret with optimized version.
"""

import asyncio
import time
import logging
import argparse
import os
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
        Tuple of (results, execution_time)
    """
    from maigret.checking import maigret
    from maigret.sites import MaigretDatabase
    
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
    
    return results, execution_time


async def benchmark_optimized(username, sites_count=100, timeout=10):
    """
    Benchmark the optimized Maigret implementation.
    
    Args:
        username: Username to check
        sites_count: Number of sites to check
        timeout: Request timeout
        
    Returns:
        Tuple of (results, execution_time)
    """
    from maigret.optimized_maigret import maigret
    from maigret.optimized_sites import LazyMaigretDatabase
    
    # Get database
    db_file = os.path.join("maigret", "resources", "data.json")
    db = LazyMaigretDatabase.get_instance(db_file)
    
    # Get sites (only top N)
    sites = db.get_popular_sites(sites_count)
    
    # Start timer
    start_time = time.time()
    
    # Run search
    results = await maigret(
        username=username,
        sites_data={"sites": sites},
        timeout=timeout,
        logger=logger
    )
    
    # Calculate time
    execution_time = time.time() - start_time
    
    return results, execution_time


async def run_benchmark(usernames, sites_count=100, timeout=10):
    """
    Run the benchmark on multiple usernames.
    
    Args:
        usernames: List of usernames to check
        sites_count: Number of sites to check
        timeout: Request timeout
    """
    original_times = []
    optimized_times = []
    
    for username in usernames:
        logger.info(f"Benchmarking username: {username}")
        
        # Run original version
        logger.info("Running original implementation...")
        original_results, original_time = await benchmark_original(
            username, 
            sites_count=sites_count,
            timeout=timeout
        )
        original_times.append(original_time)
        
        logger.info(f"Original time: {original_time:.2f}s")
        
        # Run optimized version
        logger.info("Running optimized implementation...")
        optimized_results, optimized_time = await benchmark_optimized(
            username,
            sites_count=sites_count,
            timeout=timeout
        )
        optimized_times.append(optimized_time)
        
        logger.info(f"Optimized time: {optimized_time:.2f}s")
        
        # Calculate improvement
        improvement = ((original_time - optimized_time) / original_time) * 100
        logger.info(f"Performance improvement: {improvement:.2f}%")
        
        # Compare result counts
        original_count = len([r for r in original_results.values() 
                            if r.get("status", {}).status == "CLAIMED"])
        
        optimized_count = len([r for r in optimized_results.values() 
                             if r.get("status", {}).status == "CLAIMED"])
        
        logger.info(f"Original found: {original_count} profiles")
        logger.info(f"Optimized found: {optimized_count} profiles")
        
        # Memory usage
        import psutil
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / 1024 / 1024  # in MB
        logger.info(f"Memory usage: {memory_usage:.2f} MB")
        
        logger.info("-" * 50)
    
    # Overall statistics
    avg_original = sum(original_times) / len(original_times)
    avg_optimized = sum(optimized_times) / len(optimized_times)
    overall_improvement = ((avg_original - avg_optimized) / avg_original) * 100
    
    logger.info("=== BENCHMARK SUMMARY ===")
    logger.info(f"Number of usernames tested: {len(usernames)}")
    logger.info(f"Number of sites checked per username: {sites_count}")
    logger.info(f"Average time (original): {avg_original:.2f}s")
    logger.info(f"Average time (optimized): {avg_optimized:.2f}s")
    logger.info(f"Overall improvement: {overall_improvement:.2f}%")


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