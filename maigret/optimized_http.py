"""
Optimized HTTP module for Maigret.
Provides backward compatibility with original Maigret while using optimized implementations.
"""

import asyncio
import logging
import os
import ssl
import sys
from typing import Dict, List, Optional, Tuple, Any, Union
from urllib.parse import quote
import warnings

import aiodns
from aiohttp import ClientSession, ClientResponse, TCPConnector
from aiohttp.client_exceptions import ClientConnectorError, ServerDisconnectedError
from python_socks import _errors as proxy_errors

from .errors import CheckError
from .optimized_checker import OptimizedChecker, OptimizedHttpChecker, OptimizedDomainResolver


class MaigretHttpChecker:
    """
    Drop-in replacement for the original HTTP checker that uses optimized internals.
    Maintains backward compatibility with the original interface.
    """
    
    def __init__(self, proxy=None, cookie_jar=None, logger=None):
        """
        Initialize HTTP checker with backward-compatible interface.
        
        Args:
            proxy: Optional proxy URL
            cookie_jar: Optional cookie jar
            logger: Optional logger
        """
        self.proxy = proxy
        self.cookie_jar = cookie_jar
        self.logger = logger or logging.getLogger(__name__)
        self.url = None
        self.headers = None
        self.allow_redirects = True
        self.timeout = 0
        self.method = 'get'
        
        # Internal optimized checker
        self._checker = OptimizedHttpChecker(proxy, cookie_jar, logger)
    
    def prepare(self, url, headers=None, allow_redirects=True, timeout=0, method='get'):
        """
        Prepare request parameters (original interface).
        
        Args:
            url: URL to request
            headers: Optional request headers
            allow_redirects: Whether to follow redirects
            timeout: Request timeout in seconds
            method: HTTP method ('get' or 'head')
        """
        self.url = url
        self.headers = headers
        self.allow_redirects = allow_redirects
        self.timeout = timeout
        self.method = method
        
        # Update internal checker
        self._checker.prepare(url, headers, allow_redirects, timeout, method)
        return None
    
    async def check(self) -> Tuple[str, int, Optional[CheckError]]:
        """
        Perform HTTP check using optimized implementation.
        
        Returns:
            Tuple of (response text, status code, error)
        """
        return await self._checker.check()
    
    async def close(self):
        """Close resources (not needed for optimized implementation)."""
        pass


class MaigretDomainResolver:
    """
    Backward-compatible domain resolver that uses optimized implementation.
    """
    
    def __init__(self, logger=None):
        """
        Initialize domain resolver.
        
        Args:
            logger: Optional logger
        """
        self.logger = logger or logging.getLogger(__name__)
        self.url = None
        
        # Internal optimized resolver
        self._resolver = OptimizedDomainResolver(logger)
    
    def prepare(self, url, headers=None, allow_redirects=True, timeout=0, method='get'):
        """
        Prepare domain resolver (original interface).
        
        Args:
            url: Domain to resolve
            headers: Not used, kept for compatibility
            allow_redirects: Not used, kept for compatibility
            timeout: Not used, kept for compatibility
            method: Not used, kept for compatibility
        """
        self.url = url
        self._resolver.prepare(url)
        return None
    
    async def check(self) -> Tuple[str, int, Optional[CheckError]]:
        """
        Perform DNS resolution using optimized implementation.
        
        Returns:
            Tuple of (IP address, status code, error)
        """
        return await self._resolver.check()
    
    async def close(self):
        """Close resources (not needed for optimized implementation)."""
        pass


# Global cleanup function
async def cleanup_resources():
    """Clean up all shared resources."""
    await OptimizedChecker.cleanup()


# Helper functions for backward compatibility
def get_maigret_http_checker(proxy=None, cookie_jar=None, logger=None) -> MaigretHttpChecker:
    """Get a backward-compatible HTTP checker with optimized internals."""
    return MaigretHttpChecker(proxy, cookie_jar, logger)


def get_maigret_domain_resolver(logger=None) -> MaigretDomainResolver:
    """Get a backward-compatible domain resolver with optimized internals."""
    return MaigretDomainResolver(logger)