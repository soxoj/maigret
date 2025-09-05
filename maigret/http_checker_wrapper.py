"""
Backward-compatible wrapper for Maigret's HTTP checking mechanisms.
Provides seamless integration of the optimized HTTP checker.
"""

import logging
import sys
from typing import Dict, List, Optional, Tuple, Any

from .errors import CheckError
from .optimized_http import MaigretHttpChecker, MaigretDomainResolver, cleanup_resources

# Import original checkers for compatibility
from .checking import (
    SimpleAiohttpChecker,
    ProxiedAiohttpChecker,
    AiodnsDomainResolver,
    CheckerMock,
)


def get_http_checker(
    checker_type="simple", proxy=None, cookie_jar=None, logger=None
):
    """
    Factory function to create an appropriate HTTP checker.
    Uses optimized checkers when available, falling back to original ones if needed.
    
    Args:
        checker_type: Type of checker to create ('simple', 'proxied', 'dns', 'mock')
        proxy: Optional proxy URL
        cookie_jar: Optional cookie jar
        logger: Optional logger
        
    Returns:
        An HTTP checker instance
    """
    logger = logger or logging.getLogger(__name__)
    
    # Use optimized checkers by default
    if checker_type == "simple":
        return MaigretHttpChecker(proxy=proxy, cookie_jar=cookie_jar, logger=logger)
    elif checker_type == "proxied":
        return MaigretHttpChecker(proxy=proxy, cookie_jar=cookie_jar, logger=logger)
    elif checker_type == "dns":
        return MaigretDomainResolver(logger=logger)
    elif checker_type == "mock":
        return CheckerMock()
    else:
        # Fallback to original checkers if needed
        logger.warning(f"Unknown checker type: {checker_type}, using simple")
        return SimpleAiohttpChecker(proxy=proxy, cookie_jar=cookie_jar, logger=logger)


async def close_http_checkers():
    """
    Close all HTTP checkers and release resources.
    """
    await cleanup_resources()


# Create a mapping for backwards compatibility
HTTP_CHECKER_TYPES = {
    "simple": SimpleAiohttpChecker,
    "proxied": ProxiedAiohttpChecker,
    "dns": AiodnsDomainResolver,
    "mock": CheckerMock,
    # Add optimized versions
    "optimized": MaigretHttpChecker,
    "optimized_dns": MaigretDomainResolver,
}


def update_checker_mapping(use_optimized=True):
    """
    Update the global checker mapping to use optimized or original checkers.
    
    Args:
        use_optimized: Whether to use optimized checkers
    """
    global HTTP_CHECKER_TYPES
    
    if use_optimized:
        # Replace standard checkers with optimized ones
        HTTP_CHECKER_TYPES["simple"] = MaigretHttpChecker
        HTTP_CHECKER_TYPES["proxied"] = MaigretHttpChecker
        HTTP_CHECKER_TYPES["dns"] = MaigretDomainResolver
    else:
        # Restore original checkers
        HTTP_CHECKER_TYPES["simple"] = SimpleAiohttpChecker
        HTTP_CHECKER_TYPES["proxied"] = ProxiedAiohttpChecker  
        HTTP_CHECKER_TYPES["dns"] = AiodnsDomainResolver