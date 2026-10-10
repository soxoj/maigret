"""
OpenAPI 3.0 specification for the Maigret REST API.

This module provides the OpenAPI schema for the REST API endpoints.
"""

OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "Maigret OSINT API",
        "description": "REST API for conducting OSINT searches using Maigret",
        "version": "1.0.0",
        "contact": {
            "name": "Maigret Project",
            "url": "https://github.com/soxoj/maigret"
        },
        "license": {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT"
        }
    },
    "servers": [
        {
            "url": "http://localhost:5000/api/v1",
            "description": "Development server"
        }
    ],
    "components": {
        "securitySchemes": {
            "ApiKeyHeader": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API key in X-API-Key header"
            },
            "BearerToken": {
                "type": "http",
                "scheme": "bearer",
                "description": "Bearer token in Authorization header"
            }
        },
        "schemas": {
            "SearchRequest": {
                "type": "object",
                "required": ["username"],
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "Username to search for"
                    },
                    "sites": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of site names to search (null or omitted means all)"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Request timeout in seconds (default: 10)"
                    },
                    "retries": {
                        "type": "integer",
                        "description": "Number of retries for failed requests (default: 1)"
                    }
                }
            },
            "SearchResponse": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "Unique identifier for the search job"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["accepted", "running", "completed", "failed", "cancelled"],
                        "description": "Current status of the search"
                    },
                    "message": {
                        "type": "string",
                        "description": "Human-readable status message"
                    }
                }
            },
            "SearchResult": {
                "type": "object",
                "properties": {
                    "site": {
                        "type": "string",
                        "description": "Name of the site checked"
                    },
                    "username": {
                        "type": "string",
                        "description": "Username searched for"
                    },
                    "url": {
                        "type": "string",
                        "nullable": True,
                        "description": "URL of the found profile (if status is 'found')"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["found", "not_found", "error", "unknown"],
                        "description": "Result status for this site"
                    },
                    "error": {
                        "type": "string",
                        "nullable": True,
                        "description": "Error message if status is 'error'"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional information extracted from the profile"
                    }
                }
            },
            "SearchStatus": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "Unique identifier for the search job"
                    },
                    "username": {
                        "type": "string",
                        "description": "Username being searched for"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "running", "completed", "failed", "cancelled"],
                        "description": "Current status of the search"
                    },
                    "progress": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "Progress as a percentage (0-100)"
                    },
                    "results_count": {
                        "type": "integer",
                        "description": "Number of results found so far"
                    },
                    "results": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/SearchResult"},
                        "description": "List of search results"
                    },
                    "error": {
                        "type": "string",
                        "nullable": True,
                        "description": "Error message if search failed"
                    },
                    "started_at": {
                        "type": "string",
                        "format": "date-time",
                        "nullable": True,
                        "description": "Timestamp when search started"
                    },
                    "completed_at": {
                        "type": "string",
                        "format": "date-time",
                        "nullable": True,
                        "description": "Timestamp when search completed"
                    }
                }
            },
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "description": "Error type (e.g., 'Bad Request', 'Unauthorized')"
                    },
                    "message": {
                        "type": "string",
                        "description": "Error message"
                    },
                    "code": {
                        "type": "string",
                        "description": "Error code for programmatic handling"
                    }
                }
            }
        }
    },
    "security": [
        {"ApiKeyHeader": []},
        {"BearerToken": []}
    ],
    "paths": {
        "/health": {
            "get": {
                "tags": ["System"],
                "summary": "Health check",
                "description": "Check if the API is running (no authentication required)",
                "security": [],
                "responses": {
                    "200": {
                        "description": "API is healthy",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "message": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "/search": {
            "post": {
                "tags": ["Search"],
                "summary": "Start a new search",
                "description": "Initiate a new OSINT search for a username",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/SearchRequest"}
                        }
                    }
                },
                "responses": {
                    "202": {
                        "description": "Search job accepted",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SearchResponse"}
                            }
                        }
                    },
                    "400": {
                        "description": "Invalid request",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    },
                    "401": {
                        "description": "Unauthorized - missing or invalid API key"
                    }
                }
            }
        },
        "/search/{job_id}": {
            "get": {
                "tags": ["Search"],
                "summary": "Get search results",
                "description": "Retrieve results for a completed or in-progress search",
                "parameters": [
                    {
                        "name": "job_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"},
                        "description": "Job ID returned from /search POST"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Search results",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SearchStatus"}
                            }
                        }
                    },
                    "401": {
                        "description": "Unauthorized"
                    },
                    "404": {
                        "description": "Job not found"
                    }
                }
            },
            "delete": {
                "tags": ["Search"],
                "summary": "Cancel a search",
                "description": "Cancel an in-progress search job",
                "parameters": [
                    {
                        "name": "job_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Search cancelled",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "job_id": {"type": "string"},
                                        "status": {"type": "string"},
                                        "message": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "401": {
                        "description": "Unauthorized"
                    },
                    "404": {
                        "description": "Job not found"
                    }
                }
            }
        },
        "/search/{job_id}/status": {
            "get": {
                "tags": ["Search"],
                "summary": "Stream search progress",
                "description": "Stream real-time progress updates via Server-Sent Events",
                "parameters": [
                    {
                        "name": "job_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Event stream",
                        "content": {
                            "text/event-stream": {
                                "schema": {
                                    "type": "string"
                                }
                            }
                        }
                    },
                    "401": {
                        "description": "Unauthorized"
                    },
                    "404": {
                        "description": "Job not found"
                    }
                }
            }
        }
    }
}


def get_openapi_spec():
    """Get the OpenAPI specification."""
    return OPENAPI_SPEC
