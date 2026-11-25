"""Proxy transport rules shared by profile checks and activation requests."""

import logging
from typing import Any, Dict, Optional
from urllib.parse import urlsplit

from aiohttp_socks import ProxyConnector

logger = logging.getLogger(__name__)

PYTHON_SOCKS_TRANSPORT = 'python_socks'
LIBCURL_TRANSPORT = 'libcurl'
REQUESTS_TRANSPORT = 'requests'

# python_socks already resolves SOCKS5 names remotely; curl/requests need the h.
_PROXY_SCHEME_ALIASES = {
    PYTHON_SOCKS_TRANSPORT: {'socks5h': 'socks5'},
    LIBCURL_TRANSPORT: {'socks5': 'socks5h'},
    REQUESTS_TRANSPORT: {'socks5': 'socks5h'},
}


def normalize_proxy_scheme(proxy: Optional[str], transport: str) -> Optional[str]:
    """Normalize only the scheme, preserving credentials and proxy identity."""
    if not proxy:
        return proxy
    scheme, separator, remainder = proxy.partition('://')
    if not separator:
        return proxy
    replacement = _PROXY_SCHEME_ALIASES[transport].get(scheme.lower())
    if replacement is None:
        return proxy
    return f'{replacement}://{remainder}'


def validate_proxy(proxy: Optional[str], transport: str) -> None:
    """Reject unsupported routes without including credentials in the error."""
    if not proxy:
        return
    schemes = {'http', 'socks4', 'socks5', 'socks5h'}
    if transport == LIBCURL_TRANSPORT:
        schemes |= {'https', 'socks4a'}
    if urlsplit(proxy).scheme.lower() not in schemes:
        raise ValueError('Unsupported proxy scheme')


def proxy_connector(proxy: str, **kwargs: Any) -> ProxyConnector:
    validate_proxy(proxy, PYTHON_SOCKS_TRANSPORT)
    normalized = normalize_proxy_scheme(proxy, PYTHON_SOCKS_TRANSPORT)
    assert normalized is not None
    return ProxyConnector.from_url(normalized, **kwargs)


def activation_session_options(proxy: Optional[str]) -> Dict[str, Any]:
    options: Dict[str, Any] = {'trust_env': not bool(proxy), 'raise_for_status': True}
    if proxy:
        options['connector'] = proxy_connector(proxy)
    return options
