"""
Integration tests for the REST API endpoints.

Tests full endpoint workflows including authentication and responses.
"""

import pytest
import json
import os
from unittest.mock import patch, MagicMock, Mock

# pytest fixture for Flask test client
@pytest.fixture
def app():
    """Create and configure a test Flask app."""
    # Set the API key in environment before importing the app
    os.environ['MAIGRET_API_KEYS'] = 'default-api-key-change-in-production'
    
    from maigret.web.app import app
    from maigret.api.config import reload_keys
    
    app.config['TESTING'] = True
    
    # Reload API keys from the environment variable we just set
    reload_keys()
    
    yield app
    
    # Clean up
    if 'MAIGRET_API_KEYS' in os.environ:
        del os.environ['MAIGRET_API_KEYS']


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def api_key():
    """Use the default test API key."""
    return 'default-api-key-change-in-production'


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check_success(self, client):
        """Test health check endpoint."""
        response = client.get('/api/v1/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'

    def test_health_check_no_auth(self, client):
        """Test that health check doesn't require authentication."""
        response = client.get('/api/v1/health')
        assert response.status_code == 200


class TestSearchEndpoint:
    """Tests for the search endpoint."""

    def test_search_missing_api_key(self, client):
        """Test search without API key."""
        response = client.post(
            '/api/v1/search',
            data=json.dumps({'username': 'test_user'}),
            content_type='application/json'
        )
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Unauthorized'
        assert data['code'] == 'MISSING_API_KEY'

    def test_search_invalid_api_key(self, client):
        """Test search with invalid API key."""
        response = client.post(
            '/api/v1/search',
            data=json.dumps({'username': 'test_user'}),
            content_type='application/json',
            headers={'X-API-Key': 'invalid-key'}
        )
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Unauthorized'
        assert data['code'] == 'INVALID_API_KEY'

    def test_search_with_valid_api_key_header(self, client, api_key):
        """Test search with valid API key in header."""
        response = client.post(
            '/api/v1/search',
            data=json.dumps({'username': 'test_user'}),
            content_type='application/json',
            headers={'X-API-Key': api_key}
        )
        assert response.status_code == 202
        data = json.loads(response.data)
        assert 'job_id' in data
        assert data['status'] == 'accepted'

    def test_search_with_bearer_token(self, client, api_key):
        """Test search with Bearer token in Authorization header."""
        response = client.post(
            '/api/v1/search',
            data=json.dumps({'username': 'test_user'}),
            content_type='application/json',
            headers={'Authorization': f'Bearer {api_key}'}
        )
        assert response.status_code == 202
        data = json.loads(response.data)
        assert 'job_id' in data

    def test_search_with_query_parameter(self, client, api_key):
        """Test search with API key as query parameter."""
        response = client.post(
            f'/api/v1/search?api_key={api_key}',
            data=json.dumps({'username': 'test_user'}),
            content_type='application/json'
        )
        assert response.status_code == 202
        data = json.loads(response.data)
        assert 'job_id' in data

    def test_search_missing_username(self, client, api_key):
        """Test search with missing username."""
        response = client.post(
            '/api/v1/search',
            data=json.dumps({}),
            content_type='application/json',
            headers={'X-API-Key': api_key}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'Bad Request'
        assert data['code'] in ['VALIDATION_ERROR', 'INVALID_REQUEST']

    def test_search_empty_username(self, client, api_key):
        """Test search with empty username."""
        response = client.post(
            '/api/v1/search',
            data=json.dumps({'username': '   '}),
            content_type='application/json',
            headers={'X-API-Key': api_key}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'Bad Request'

    def test_search_invalid_json(self, client, api_key):
        """Test search with invalid JSON."""
        response = client.post(
            '/api/v1/search',
            data='invalid json',
            content_type='application/json',
            headers={'X-API-Key': api_key}
        )
        assert response.status_code == 400

    def test_search_returns_job_id(self, client, api_key):
        """Test that search returns a job ID."""
        response = client.post(
            '/api/v1/search',
            data=json.dumps({
                'username': 'test_user',
                'timeout': 10,
                'retries': 2
            }),
            content_type='application/json',
            headers={'X-API-Key': api_key}
        )
        assert response.status_code == 202
        data = json.loads(response.data)
        assert 'job_id' in data
        assert len(data['job_id']) > 0


class TestResultsEndpoint:
    """Tests for the results endpoint."""

    def test_results_missing_api_key(self, client):
        """Test results endpoint without API key."""
        response = client.get('/api/v1/search/test-job-id')
        assert response.status_code == 401

    def test_results_job_not_found(self, client, api_key):
        """Test results for non-existent job."""
        response = client.get(
            '/api/v1/search/nonexistent-job-id',
            headers={'X-API-Key': api_key}
        )
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['code'] == 'JOB_NOT_FOUND'

    def test_results_success(self, client, api_key):
        """Test successful results retrieval."""
        # First create a job
        search_response = client.post(
            '/api/v1/search',
            data=json.dumps({'username': 'test_user'}),
            content_type='application/json',
            headers={'X-API-Key': api_key}
        )
        job_id = json.loads(search_response.data)['job_id']

        # Then retrieve results
        response = client.get(
            f'/api/v1/search/{job_id}',
            headers={'X-API-Key': api_key}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['job_id'] == job_id
        assert data['username'] == 'test_user'
        assert 'status' in data
        assert 'results' in data


class TestCancelEndpoint:
    """Tests for the cancel endpoint."""

    def test_cancel_missing_api_key(self, client):
        """Test cancel without API key."""
        response = client.delete('/api/v1/search/test-job-id')
        assert response.status_code == 401

    def test_cancel_job_not_found(self, client, api_key):
        """Test cancel for non-existent job."""
        response = client.delete(
            '/api/v1/search/nonexistent-job-id',
            headers={'X-API-Key': api_key}
        )
        assert response.status_code == 404

    def test_cancel_success(self, client, api_key):
        """Test successful job cancellation."""
        # Create a job
        search_response = client.post(
            '/api/v1/search',
            data=json.dumps({'username': 'test_user'}),
            content_type='application/json',
            headers={'X-API-Key': api_key}
        )
        job_id = json.loads(search_response.data)['job_id']

        # Cancel it
        response = client.delete(
            f'/api/v1/search/{job_id}',
            headers={'X-API-Key': api_key}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['job_id'] == job_id
        assert data['status'] == 'cancelled'


class TestErrorHandling:
    """Tests for error handling."""

    def test_404_endpoint_not_found(self, client, api_key):
        """Test 404 for non-existent endpoint."""
        response = client.get(
            '/api/v1/nonexistent',
            headers={'X-API-Key': api_key}
        )
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['code'] == 'ENDPOINT_NOT_FOUND'

    def test_405_method_not_allowed(self, client, api_key):
        """Test 405 for invalid HTTP method."""
        response = client.patch(
            '/api/v1/health',
            headers={'X-API-Key': api_key}
        )
        assert response.status_code == 405
        # Flask's default 405 handler may not return JSON, so just verify the status code
