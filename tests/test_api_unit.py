"""
Unit tests for the REST API endpoints and components.

Tests API authentication, validation, endpoint responses, and error handling.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock

from maigret.api.config import APIKeyStore, APIConfig
from maigret.api.schemas import (
    SearchRequest, SearchResult, SearchStatus, validate_search_request
)
from maigret.api.job_manager import JobManager, get_job_manager


class TestAPIKeyStore:
    """Tests for API key management."""

    def test_api_key_store_init(self):
        """Test API key store initialization."""
        store = APIKeyStore()
        # Should have loaded from env, but for testing let's add keys manually
        assert isinstance(store.keys, set)

    def test_add_key(self):
        """Test adding a new API key."""
        store = APIKeyStore()
        store.add_key('test-key')
        assert store.validate_key('test-key')

    def test_remove_key(self):
        """Test removing an API key."""
        store = APIKeyStore()
        store.add_key('test-key')
        assert store.validate_key('test-key')
        store.remove_key('test-key')
        assert not store.validate_key('test-key')

    def test_validate_key_valid(self):
        """Test validating a valid API key."""
        store = APIKeyStore(['valid-key'])
        assert store.validate_key('valid-key')

    def test_validate_key_invalid(self):
        """Test validating an invalid API key."""
        store = APIKeyStore(['valid-key'])
        assert not store.validate_key('invalid-key')

    def test_get_all_keys(self):
        """Test retrieving all API keys."""
        store = APIKeyStore(['key1', 'key2'])
        keys = store.get_all_keys()
        assert len(keys) == 2
        assert 'key1' in keys
        assert 'key2' in keys

    def test_clear_all(self):
        """Test clearing all API keys."""
        store = APIKeyStore(['key1', 'key2'])
        count = store.clear_all()
        assert count == 2
        assert len(store.get_all_keys()) == 0


class TestAPIConfig:
    """Tests for API configuration."""

    def test_config_init_defaults(self):
        """Test configuration with defaults."""
        config = APIConfig()
        assert config.enabled is True
        assert config.max_jobs == 1000
        assert config.default_timeout == 10

    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = APIConfig(max_jobs=500)
        data = config.to_dict()
        assert data['max_jobs'] == 500
        assert data['enabled'] is True


class TestSchemas:
    """Tests for request/response schemas."""

    def test_search_request_valid(self):
        """Test creating a valid search request."""
        req = SearchRequest(
            username='test_user',
            sites=['GitHub', 'Twitter'],
            timeout=10,
        )
        assert req.username == 'test_user'
        assert req.sites == ['GitHub', 'Twitter']
        assert req.timeout == 10

    def test_search_request_to_dict(self):
        """Test converting search request to dictionary."""
        req = SearchRequest(username='test_user', timeout=10)
        data = req.to_dict()
        assert data['username'] == 'test_user'
        assert data['timeout'] == 10
        assert 'sites' not in data  # None values excluded

    def test_search_result_creation(self):
        """Test creating a search result."""
        result = SearchResult(
            site='GitHub',
            username='test_user',
            url='https://github.com/test_user',
            status='found',
        )
        assert result.site == 'GitHub'
        assert result.status == 'found'

    def test_search_status_creation(self):
        """Test creating a search status."""
        status = SearchStatus(
            job_id='123',
            username='test_user',
            status='running',
            progress=50,
        )
        assert status.job_id == '123'
        assert status.progress == 50

    def test_validate_search_request_valid(self):
        """Test validating a valid search request."""
        data = {'username': 'test_user', 'timeout': 10}
        req = validate_search_request(data)
        assert req.username == 'test_user'
        assert req.timeout == 10

    def test_validate_search_request_missing_username(self):
        """Test validating request with missing username."""
        data = {'timeout': 10}
        with pytest.raises(ValueError, match='username is required'):
            validate_search_request(data)

    def test_validate_search_request_empty_username(self):
        """Test validating request with empty username."""
        data = {'username': '   ', 'timeout': 10}
        with pytest.raises(ValueError, match='username is required'):
            validate_search_request(data)

    def test_validate_search_request_invalid_type(self):
        """Test validating invalid request type."""
        with pytest.raises(ValueError, match='Request body must be a JSON object'):
            validate_search_request('not a dict')


class TestJobManager:
    """Tests for job management."""

    def test_create_job(self):
        """Test creating a job."""
        manager = JobManager()
        job_id = manager.create_job('test_user')
        assert job_id
        assert manager.get_job(job_id)

    def test_get_job_not_found(self):
        """Test getting a non-existent job."""
        manager = JobManager()
        assert manager.get_job('nonexistent') is None

    def test_get_status(self):
        """Test getting job status."""
        manager = JobManager()
        job_id = manager.create_job('test_user')
        status = manager.get_status(job_id)
        assert status.job_id == job_id
        assert status.status == 'pending'

    def test_update_status(self):
        """Test updating job status."""
        manager = JobManager()
        job_id = manager.create_job('test_user')
        manager.update_status(job_id, 'running', 50)
        status = manager.get_status(job_id)
        assert status.status == 'running'
        assert status.progress == 50

    def test_add_result(self):
        """Test adding a result to a job."""
        manager = JobManager()
        job_id = manager.create_job('test_user')
        result = SearchResult(site='GitHub', username='test_user', status='found')
        manager.add_result(job_id, result)
        status = manager.get_status(job_id)
        assert len(status.results) == 1
        assert status.results_count == 1

    def test_set_error(self):
        """Test setting error on a job."""
        manager = JobManager()
        job_id = manager.create_job('test_user')
        manager.set_error(job_id, 'Test error')
        status = manager.get_status(job_id)
        assert status.status == 'failed'
        assert status.error == 'Test error'

    def test_cancel_job(self):
        """Test cancelling a job."""
        manager = JobManager()
        job_id = manager.create_job('test_user')
        manager.update_status(job_id, 'running')
        manager.cancel_job(job_id)
        status = manager.get_status(job_id)
        assert status.status == 'cancelled'

    def test_cleanup_job(self):
        """Test cleaning up a job."""
        manager = JobManager()
        job_id = manager.create_job('test_user')
        assert manager.get_job(job_id)
        manager.cleanup_job(job_id)
        assert manager.get_job(job_id) is None

    def test_max_jobs_limit(self):
        """Test that old jobs are removed when max is reached."""
        manager = JobManager(max_jobs=2)
        job1 = manager.create_job('user1')
        job2 = manager.create_job('user2')
        assert len(manager.jobs) == 2
        job3 = manager.create_job('user3')
        # job1 should be removed, only job2 and job3 remain
        assert len(manager.jobs) == 2
        assert manager.get_job(job1) is None
        assert manager.get_job(job2) is not None
        assert manager.get_job(job3) is not None
