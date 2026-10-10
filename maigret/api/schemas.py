"""
Request and response schemas for the REST API.

Uses Python dataclasses for type validation and serialization.
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class SearchRequest:
    """Schema for a search request."""
    username: str
    sites: Optional[List[str]] = None
    timeout: Optional[int] = None
    retries: Optional[int] = None
    proxies: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class SearchResult:
    """Schema for a single search result."""
    site: str
    username: str
    url: Optional[str] = None
    status: str = "unknown"  # "found", "not_found", "error", "unknown"
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SearchStatus:
    """Schema for search progress/status."""
    job_id: str
    username: str
    status: str = "pending"  # "pending", "running", "completed", "failed", "cancelled"
    progress: int = 0  # percentage 0-100
    results_count: int = 0
    results: List[SearchResult] = field(default_factory=list)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with datetime serialization."""
        data = asdict(self)
        data['results'] = [r.to_dict() for r in self.results]
        data['started_at'] = self.started_at.isoformat() if self.started_at else None
        data['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        return data


@dataclass
class SearchResponse:
    """Schema for initial search response."""
    job_id: str
    status: str = "accepted"
    message: str = "Search job created"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ErrorResponse:
    """Schema for error responses."""
    error: str
    message: str
    code: str = "INTERNAL_ERROR"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


def validate_search_request(data: Dict[str, Any]) -> SearchRequest:
    """Validate and parse a search request from JSON."""
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object")

    username = data.get('username', '').strip()
    if not username:
        raise ValueError("username is required and must not be empty")

    return SearchRequest(
        username=username,
        sites=data.get('sites'),
        timeout=data.get('timeout'),
        retries=data.get('retries'),
        proxies=data.get('proxies'),
    )
