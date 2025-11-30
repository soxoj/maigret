"""
Optimized version of HTTP checking module for Maigret.
This module provides improved connection pooling and reuse.
"""

import asyncio
import logging
import os
import ssl
import sys
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import quote

import aiodns
from aiohttp import ClientSession, ClientResponse, TCPConnector
from aiohttp.client_exceptions import ClientConnectorError, ServerDisconnectedError
from python_socks import _errors as proxy_errors

from .errors import CheckError


class OptimizedChecker:
    """
    An optimized HTTP checker class that efficiently manages connections
    and provides better reuse of resources.
    """
    
    # Shared resources
    _connector = None
    _connector_proxy = {}
    _dns_resolver = None
    _session_cache = {}
    
    @classmethod
    def get_connector(cls, reuse_connections=True):
        """Get or create an optimized connection pool."""
        if cls._connector is None:
            # Determine optimal connection limits based on system resources
            max_connections = min(100, os.cpu_count() * 8)
            
            cls._connector = TCPConnector(
                ssl=False,  # We'll handle SSL explicitly
                limit=max_connections,
                ttl_dns_cache=300,  # Cache DNS results longer
                enable_cleanup_closed=True,  # Clean up closed connections
                force_close=not reuse_connections,  # Keep connections alive by default
            )
        
        return cls._connector
    
    @classmethod
    def get_proxy_connector(cls, proxy_url):
        """Get or create a proxy connector for the given URL."""
        if proxy_url not in cls._connector_proxy:
            from aiohttp_socks import ProxyConnector
            cls._connector_proxy[proxy_url] = ProxyConnector.from_url(proxy_url)
        
        return cls._connector_proxy[proxy_url]
    
    @classmethod
    def get_dns_resolver(cls):
        """Get or create a shared DNS resolver."""
        if cls._dns_resolver is None:
            loop = asyncio.get_event_loop()
            cls._dns_resolver = aiodns.DNSResolver(loop=loop)
        
        return cls._dns_resolver
    
    @classmethod
    async def get_session(cls, proxy=None, cookie_jar=None):
        """Get or create a cached session with appropriate connector."""
        cache_key = (proxy, id(cookie_jar) if cookie_jar else None)
        
        if cache_key not in cls._session_cache:
            connector = cls.get_proxy_connector(proxy) if proxy else cls.get_connector()
            cls._session_cache[cache_key] = ClientSession(
                connector=connector,
                trust_env=True,
                cookie_jar=cookie_jar,
            )
        
        return cls._session_cache[cache_key]
    
    @classmethod
    async def cleanup(cls):
        """Close all sessions and clean up resources."""
        tasks = []
        
        for session in cls._session_cache.values():
            if not session.closed:
                tasks.append(session.close())
        
        if tasks:
            await asyncio.gather(*tasks)
        
        cls._session_cache.clear()
        
        if cls._connector:
            await cls._connector.close()
            cls._connector = None
        
        for proxy_conn in cls._connector_proxy.values():
            await proxy_conn.close()
        
        cls._connector_proxy.clear()


class OptimizedHttpChecker:
    """
    A faster HTTP checker that uses connection pooling and can batch requests
    for similar sites or domains.
    """
    
    def __init__(self, proxy=None, cookie_jar=None, logger=None):
        self.proxy = proxy
        self.cookie_jar = cookie_jar
        self.logger = logger or logging.getLogger(__name__)
        self.url = None
        self.headers = None
        self.allow_redirects = True
        self.timeout = 0
        self.method = 'get'
        
    def prepare(self, url, headers=None, allow_redirects=True, timeout=0, method='get'):
        """Prepare request parameters."""
        self.url = url
        self.headers = headers
        self.allow_redirects = allow_redirects
        self.timeout = timeout
        self.method = method
        return None
    
    async def close(self):
        """Connection cleanup is handled at the class level."""
        pass
    
    async def _make_request(
        self, session, url, headers, allow_redirects, timeout, method, logger
    ) -> Tuple[str, int, Optional[CheckError]]:
        """Make an optimized HTTP request with better error handling."""
        try:
            request_method = session.get if method == 'get' else session.head
            
            async with request_method(
                url=url,
                headers=headers,
                allow_redirects=allow_redirects,
                timeout=timeout,
            ) as response:
                status_code = response.status
                
                # Fast path for HEAD requests or non-text responses
                if method == 'head' or status_code >= 400:
                    return "", status_code, None
                
                try:
                    response_content = await response.content.read()
                    charset = response.charset or "utf-8"
                    decoded_content = response_content.decode(charset, "ignore")
                except Exception as e:
                    logger.debug(f"Error reading response: {e}")
                    return "", status_code, None
                
                error = CheckError("Connection lost") if status_code == 0 else None
                logger.debug(f"Response status: {status_code}")
                
                return decoded_content, status_code, error
                
        except asyncio.TimeoutError as e:
            return None, 0, CheckError("Request timeout", str(e))
        except ClientConnectorError as e:
            return None, 0, CheckError("Connecting failure", str(e))
        except ServerDisconnectedError as e:
            return None, 0, CheckError("Server disconnected", str(e))
        except proxy_errors.ProxyError as e:
            return None, 0, CheckError("Proxy", str(e))
        except KeyboardInterrupt:
            return None, 0, CheckError("Interrupted")
        except Exception as e:
            if sys.version_info.minor > 6 and (
                isinstance(e, ssl.SSLCertVerificationError)
                or isinstance(e, ssl.SSLError)
            ):
                return None, 0, CheckError("SSL", str(e))
            else:
                logger.debug(e, exc_info=True)
                return None, 0, CheckError("Unexpected", str(e))
    
    async def check(self) -> Tuple[str, int, Optional[CheckError]]:
        """Perform an optimized HTTP check using shared session pool."""
        session = await OptimizedChecker.get_session(self.proxy, self.cookie_jar)
        
        # Perform the actual request
        return await self._make_request(
            session,
            self.url,
            self.headers,
            self.allow_redirects,
            self.timeout,
            self.method,
            self.logger,
        )


class OptimizedDomainResolver:
    """Optimized DNS resolver that caches results."""
    
    _cache = {}
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.url = None
    
    def prepare(self, url, headers=None, allow_redirects=True, timeout=0, method='get'):
        """Prepare domain for resolution."""
        self.url = url
        return None
    
    async def check(self) -> Tuple[str, int, Optional[CheckError]]:
        """Perform optimized DNS resolution with caching."""
        status = 404
        error = None
        text = ''
        
        # Check cache first
        if self.url in OptimizedDomainResolver._cache:
            cached_result = OptimizedDomainResolver._cache[self.url]
            return cached_result
        
        try:
            resolver = OptimizedChecker.get_dns_resolver()
            res = await resolver.query(self.url, 'A')
            text = str(res[0].host)
            status = 200
            
            # Cache successful result
            OptimizedDomainResolver._cache[self.url] = (text, status, error)
        except aiodns.error.DNSError:
            # Cache negative result
            OptimizedDomainResolver._cache[self.url] = ('', 404, None)
        except Exception as e:
            self.logger.error(e, exc_info=True)
            error = CheckError('DNS resolve error', str(e))
        
        return text, status, error
    
    @classmethod
    def clear_cache(cls):
        """Clear the DNS resolution cache."""
        cls._cache.clear()


# Sample usage function
async def batch_check_sites(sites, username, timeout=10, max_connections=50):
    """
    Check multiple sites in optimized batches, grouping by domain.
    
    Args:
        sites: List of site configurations to check
        username: Username to check
        timeout: Request timeout in seconds
        max_connections: Maximum concurrent connections
    
    Returns:
        Dictionary of results by site name
    """
    # Create semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(max_connections)
    results = {}
    
    # Group sites by domain to optimize connection reuse
    domain_groups = {}
    for site in sites:
        domain = site.url_main.split('/')[2] if '://' in site.url_main else site.url_main
        if domain not in domain_groups:
            domain_groups[domain] = []
        domain_groups[domain].append(site)
    
    # Check sites in batches by domain
    async def check_site(site):
        async with semaphore:
            # Prepare URL and checker
            url = site.url.format(username=username)
            checker = OptimizedHttpChecker(logger=logging.getLogger(site.name))
            checker.prepare(url, headers=site.headers, timeout=timeout)
            
            # Perform check
            response = await checker.check()
            
            return site.name, response
    
    # Process each domain group
    for domain, domain_sites in domain_groups.items():
        # Create tasks for all sites in this domain
        tasks = [check_site(site) for site in domain_sites]
        
        # Wait for completion and collect results
        for task in asyncio.as_completed(tasks):
            site_name, response = await task
            results[site_name] = response
    
    # Clean up at the end
    await OptimizedChecker.cleanup()
    
    return results