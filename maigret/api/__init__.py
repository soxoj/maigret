"""
REST API module for Maigret OSINT searches.

Provides programmatic access to Maigret's search capabilities via HTTP endpoints
with API key authentication.
"""

from flask import jsonify, request
from werkzeug.exceptions import NotFound, MethodNotAllowed, BadRequest

__all__ = ['get_api_blueprint', 'init_api']


def get_api_blueprint():
    """Get the Flask blueprint for the REST API."""
    from .routes import api_bp
    return api_bp


def init_api(app):
    """Initialize the REST API with a Flask app instance."""
    from .routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    
    # Register app-level error handlers for API routes
    @app.errorhandler(400)
    def handle_400(error):
        """Handle 400 errors globally, return JSON for API routes."""
        if request.path.startswith('/api/v1'):
            return jsonify({
                'error': 'Bad Request',
                'message': 'The request body is invalid',
                'code': 'INVALID_REQUEST'
            }), 400
        # For non-API routes, use Flask's default behavior
        return error
    
    @app.errorhandler(404)
    def handle_404(error):
        """Handle 404 errors globally, return JSON for API routes."""
        if request.path.startswith('/api/v1'):
            return jsonify({
                'error': 'Not Found',
                'message': 'The requested endpoint does not exist',
                'code': 'ENDPOINT_NOT_FOUND'
            }), 404
        # For non-API routes, use Flask's default behavior
        return error
    
    @app.errorhandler(405)
    def handle_405(error):
        """Handle 405 errors globally, return JSON for API routes."""
        if request.path.startswith('/api/v1'):
            return jsonify({
                'error': 'Method Not Allowed',
                'message': 'The HTTP method is not allowed for this endpoint',
                'code': 'METHOD_NOT_ALLOWED'
            }), 405
        # For non-API routes, use Flask's default behavior
        return error
