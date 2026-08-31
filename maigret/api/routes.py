"""
REST API routes and endpoints.

Implements the Flask blueprint with search endpoints.
"""

import asyncio
import logging
import json
from typing import Dict, Any

from flask import Blueprint, request, jsonify, Response
from functools import wraps

from .auth import require_api_key
from .schemas import validate_search_request, SearchStatus, SearchResult, SearchResponse, ErrorResponse
from .job_manager import get_job_manager
from .executor import start_search_job
from .openapi import get_openapi_spec

logger = logging.getLogger(__name__)

# Create the API blueprint
api_bp = Blueprint('api', __name__)


def async_endpoint(f):
    """Decorator to handle async functions in Flask endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(f(*args, **kwargs))
            return result
        finally:
            loop.close()
    return decorated_function


@api_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint (no auth required)."""
    return jsonify({'status': 'healthy', 'message': 'Maigret API is running'}), 200


@api_bp.route('/openapi.json', methods=['GET'])
def openapi_spec():
    """Get the OpenAPI specification (no auth required)."""
    return jsonify(get_openapi_spec()), 200


@api_bp.route('/search', methods=['POST'])
@require_api_key
def start_search():
    """
    Start a new search job.

    Request body:
    {
        "username": "example_user",
        "sites": ["GitHub", "Twitter"],  # optional, null means all sites
        "timeout": 10,  # optional
        "retries": 2    # optional
    }

    Returns:
    {
        "job_id": "uuid",
        "status": "accepted",
        "message": "Search job created"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Request body must be JSON',
                'code': 'INVALID_REQUEST'
            }), 400

        search_request = validate_search_request(data)
        job_manager = get_job_manager()
        job_id = job_manager.create_job(search_request.username)

        # Start the search in background
        start_search_job(
            job_id=job_id,
            username=search_request.username,
            sites=search_request.sites,
            timeout=search_request.timeout,
            retries=search_request.retries,
        )

        response = SearchResponse(job_id=job_id, status='accepted', message='Search job created')
        return jsonify(response.to_dict()), 202

    except ValueError as e:
        return jsonify({
            'error': 'Bad Request',
            'message': str(e),
            'code': 'VALIDATION_ERROR'
        }), 400
    except Exception as e:
        logger.error(f"Error starting search: {e}", exc_info=True)
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred',
            'code': 'INTERNAL_ERROR'
        }), 500


@api_bp.route('/search/<job_id>', methods=['GET'])
@require_api_key
def get_search_results(job_id: str):
    """
    Get results for a completed search job.

    Returns:
    {
        "job_id": "uuid",
        "username": "example_user",
        "status": "completed",
        "progress": 100,
        "results_count": 42,
        "results": [
            {
                "site": "GitHub",
                "username": "example_user",
                "url": "https://github.com/example_user",
                "status": "found",
                "error": null,
                "metadata": {}
            },
            ...
        ],
        "error": null,
        "started_at": "2026-08-31T18:00:00",
        "completed_at": "2026-08-31T18:05:00"
    }
    """
    try:
        job_manager = get_job_manager()
        status = job_manager.get_status(job_id)

        if not status:
            return jsonify({
                'error': 'Not Found',
                'message': f'Job {job_id} not found',
                'code': 'JOB_NOT_FOUND'
            }), 404

        return jsonify(status.to_dict()), 200

    except Exception as e:
        logger.error(f"Error retrieving search results: {e}", exc_info=True)
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred',
            'code': 'INTERNAL_ERROR'
        }), 500


@api_bp.route('/search/<job_id>/status', methods=['GET'])
@require_api_key
def stream_search_status(job_id: str):
    """
    Stream real-time search progress via Server-Sent Events (SSE).

    Returns a stream of events:
    event: status_update
    data: {"status": "running", "progress": 25, "results_count": 10}

    event: result
    data: {"site": "GitHub", "username": "...", "url": "...", "status": "found"}

    event: completed
    data: {"status": "completed", "progress": 100, "results_count": 42}
    """
    def generate():
        """Generate SSE events for search progress."""
        job_manager = get_job_manager()

        # Initial status check
        status = job_manager.get_status(job_id)
        if not status:
            yield f'event: error\ndata: {json.dumps({"error": "Job not found"})}\n\n'
            return

        # Poll for updates (simple polling; can be optimized with websockets)
        last_result_count = 0
        max_polls = 600  # 10 minutes with 1-second intervals

        for _ in range(max_polls):
            status = job_manager.get_status(job_id)
            if not status:
                yield f'event: error\ndata: {json.dumps({"error": "Job lost"})}\n\n'
                break

            # Send new results since last poll
            if len(status.results) > last_result_count:
                for result in status.results[last_result_count:]:
                    yield f'event: result\ndata: {json.dumps(result.to_dict())}\n\n'
                last_result_count = len(status.results)

            # Send status update
            yield f'event: status_update\ndata: {json.dumps({"status": status.status, "progress": status.progress, "results_count": status.results_count})}\n\n'

            # If job is complete, send final event and exit
            if status.status in ('completed', 'failed', 'cancelled'):
                yield f'event: {status.status}\ndata: {json.dumps(status.to_dict())}\n\n'
                break

            # Wait before next poll
            asyncio.sleep(1)

    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Content-Type': 'text/event-stream'
    })


@api_bp.route('/search/<job_id>', methods=['DELETE'])
@require_api_key
def cancel_search(job_id: str):
    """
    Cancel a running search job.

    Returns:
    {
        "job_id": "uuid",
        "status": "cancelled",
        "message": "Search job cancelled"
    }
    """
    try:
        job_manager = get_job_manager()

        if not job_manager.get_job(job_id):
            return jsonify({
                'error': 'Not Found',
                'message': f'Job {job_id} not found',
                'code': 'JOB_NOT_FOUND'
            }), 404

        job_manager.cancel_job(job_id)

        return jsonify({
            'job_id': job_id,
            'status': 'cancelled',
            'message': 'Search job cancelled'
        }), 200

    except Exception as e:
        logger.error(f"Error cancelling search: {e}", exc_info=True)
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred',
            'code': 'INTERNAL_ERROR'
        }), 500


@api_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'error': 'Not Found',
        'message': 'The requested endpoint does not exist',
        'code': 'ENDPOINT_NOT_FOUND'
    }), 404


@api_bp.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors."""
    return jsonify({
        'error': 'Method Not Allowed',
        'message': 'The HTTP method is not allowed for this endpoint',
        'code': 'METHOD_NOT_ALLOWED'
    }), 405


@api_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}", exc_info=True)
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred',
        'code': 'INTERNAL_ERROR'
    }), 500
