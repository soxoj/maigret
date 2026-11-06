"""
API authentication and authorization middleware.

Implements API key validation and access control.
"""

import os
from functools import wraps
from typing import Optional, Callable
from flask import request, jsonify

from .config import get_api_key_store


def extract_api_key(req: object = request) -> Optional[str]:
    """Extract API key from request headers or query parameters."""
    # Check Authorization header (Bearer token)
    auth_header = req.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:].strip()

    # Check X-API-Key header
    api_key = req.headers.get('X-API-Key')
    if api_key:
        return api_key.strip()

    # Check query parameter (less secure, but convenient for testing)
    api_key = req.args.get('api_key')
    if api_key:
        return api_key.strip()

    return None


def require_api_key(f: Callable) -> Callable:
    """Decorator to require valid API key for an endpoint."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = extract_api_key()
        key_store = get_api_key_store()

        if not api_key:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'API key is required. Provide it via Authorization header (Bearer <key>) or X-API-Key header.',
                'code': 'MISSING_API_KEY'
            }), 401

        if not key_store.validate_key(api_key):
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Invalid API key.',
                'code': 'INVALID_API_KEY'
            }), 401

        return f(*args, **kwargs)

    return decorated_function
