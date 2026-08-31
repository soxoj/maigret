"""
REST API module for Maigret OSINT searches.

Provides programmatic access to Maigret's search capabilities via HTTP endpoints
with API key authentication.
"""

__all__ = ['get_api_blueprint', 'init_api']


def get_api_blueprint():
    """Get the Flask blueprint for the REST API."""
    from .routes import api_bp
    return api_bp


def init_api(app):
    """Initialize the REST API with a Flask app instance."""
    from .routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api/v1')
