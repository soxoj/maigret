"""
API configuration and settings management.

Handles API-specific configuration options.
"""

import os
import json
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict


@dataclass
class APIConfig:
    """REST API configuration."""
    enabled: bool = True
    max_jobs: int = 1000
    job_ttl_seconds: int = 3600  # 1 hour
    enable_rate_limiting: bool = False
    rate_limit_requests_per_minute: int = 60
    default_timeout: int = 10
    default_retries: int = 1

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_env(cls) -> 'APIConfig':
        """Load configuration from environment variables."""
        return cls(
            enabled=os.getenv('MAIGRET_API_ENABLED', 'true').lower() in ['true', '1', 'yes'],
            max_jobs=int(os.getenv('MAIGRET_API_MAX_JOBS', '1000')),
            job_ttl_seconds=int(os.getenv('MAIGRET_API_JOB_TTL', '3600')),
            enable_rate_limiting=os.getenv('MAIGRET_API_RATE_LIMITING', 'false').lower() in ['true', '1', 'yes'],
            rate_limit_requests_per_minute=int(os.getenv('MAIGRET_API_RATE_LIMIT', '60')),
            default_timeout=int(os.getenv('MAIGRET_API_TIMEOUT', '10')),
            default_retries=int(os.getenv('MAIGRET_API_RETRIES', '1')),
        )

    @classmethod
    def from_file(cls, filepath: str) -> 'APIConfig':
        """Load configuration from JSON file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        except Exception as e:
            print(f"Error loading API config from {filepath}: {e}")
            return cls()


class APIKeyStore:
    """Manages API keys (runtime storage)."""

    def __init__(self, keys: Optional[List[str]] = None):
        """Initialize with optional initial keys."""
        self.keys = set(keys) if keys else set()
        self._load_from_env()

    def _load_from_env(self):
        """Load keys from environment variable."""
        env_keys = os.getenv('MAIGRET_API_KEYS', '')
        if env_keys:
            for key in env_keys.split(','):
                key = key.strip()
                if key:
                    self.keys.add(key)

    def add_key(self, key: str) -> bool:
        """Add a new API key."""
        if not key or not key.strip():
            return False
        self.keys.add(key.strip())
        return True

    def remove_key(self, key: str) -> bool:
        """Remove an API key."""
        return bool(self.keys.discard(key))

    def validate_key(self, key: str) -> bool:
        """Check if API key is valid."""
        return key in self.keys

    def get_all_keys(self) -> List[str]:
        """Get all API keys (use with caution!)."""
        return list(self.keys)

    def clear_all(self) -> int:
        """Clear all API keys. Returns count removed."""
        count = len(self.keys)
        self.keys.clear()
        return count


# Global configuration instances
_api_config = APIConfig.from_env()
_api_key_store = APIKeyStore()


def get_api_config() -> APIConfig:
    """Get the global API configuration."""
    return _api_config


def get_api_key_store() -> APIKeyStore:
    """Get the global API key store."""
    return _api_key_store


def reload_config():
    """Reload configuration from environment."""
    global _api_config
    _api_config = APIConfig.from_env()


def reload_keys():
    """Reload API keys from environment."""
    global _api_key_store
    _api_key_store = APIKeyStore()
