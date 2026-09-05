# Maigret REST API

The Maigret REST API provides programmatic access to OSINT search capabilities via HTTP endpoints with API key authentication.

## Overview

The REST API allows external applications to:
- Initiate OSINT searches for usernames
- Retrieve search results in structured JSON format
- Monitor real-time search progress via Server-Sent Events
- Cancel ongoing searches

## Authentication

All endpoints (except `/health` and `/openapi.json`) require API key authentication. Provide your API key using one of these methods:

### 1. X-API-Key Header (Recommended)
```bash
curl -H "X-API-Key: your-api-key" https://api.example.com/api/v1/search
```

### 2. Authorization Header (Bearer Token)
```bash
curl -H "Authorization: Bearer your-api-key" https://api.example.com/api/v1/search
```

### 3. Query Parameter (for testing only)
```bash
curl https://api.example.com/api/v1/search?api_key=your-api-key
```

## API Keys

Set API keys via the `MAIGRET_API_KEYS` environment variable (comma-separated list):
```bash
export MAIGRET_API_KEYS="key1,key2,key3"
```

## Endpoints

### Health Check
**GET** `/api/v1/health`

No authentication required. Check if the API is running.

**Response:**
```json
{
  "status": "healthy",
  "message": "Maigret API is running"
}
```

### OpenAPI Specification
**GET** `/api/v1/openapi.json`

No authentication required. Get the full OpenAPI 3.0 specification.

### Start a Search
**POST** `/api/v1/search`

Initiate a new OSINT search for a username.

**Request Body:**
```json
{
  "username": "john_doe",
  "sites": ["GitHub", "Twitter"],
  "timeout": 10,
  "retries": 2
}
```

- `username` (required): Username to search for
- `sites` (optional): Array of site names to search. Omit or pass `null` to search all sites
- `timeout` (optional): Request timeout in seconds (default: 10)
- `retries` (optional): Number of retries for failed requests (default: 1)

**Response (202 Accepted):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted",
  "message": "Search job created"
}
```

### Get Search Results
**GET** `/api/v1/search/{job_id}`

Retrieve results for a search job. Returns current status even if still running.

**Response (200 OK):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "status": "completed",
  "progress": 100,
  "results_count": 5,
  "results": [
    {
      "site": "GitHub",
      "username": "john_doe",
      "url": "https://github.com/john_doe",
      "status": "found",
      "error": null,
      "metadata": {
        "ids": {
          "bio": "Software Developer",
          "location": "San Francisco"
        }
      }
    },
    {
      "site": "Twitter",
      "username": "john_doe",
      "url": null,
      "status": "not_found",
      "error": null,
      "metadata": {}
    }
  ],
  "error": null,
  "started_at": "2026-08-31T18:00:00",
  "completed_at": "2026-08-31T18:05:00"
}
```

### Stream Search Progress
**GET** `/api/v1/search/{job_id}/status`

Stream real-time search progress via Server-Sent Events.

**Events:**

`status_update`: Status and progress update
```
event: status_update
data: {"status": "running", "progress": 25, "results_count": 3}
```

`result`: New result found
```
event: result
data: {"site": "GitHub", "username": "john_doe", "url": "https://github.com/john_doe", "status": "found", ...}
```

`completed`: Search completed
```
event: completed
data: {"status": "completed", "progress": 100, "results_count": 5, ...}
```

`error`: Error occurred
```
event: error
data: {"error": "Search failed", "message": "Connection timeout"}
```

### Cancel a Search
**DELETE** `/api/v1/search/{job_id}`

Cancel an in-progress search job.

**Response (200 OK):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "message": "Search job cancelled"
}
```

## Error Responses

All errors include:
- `error`: Error type
- `message`: Detailed message
- `code`: Error code for programmatic handling

**Example Error (400 Bad Request):**
```json
{
  "error": "Bad Request",
  "message": "username is required and must not be empty",
  "code": "VALIDATION_ERROR"
}
```

**Common Error Codes:**
- `MISSING_API_KEY`: API key not provided
- `INVALID_API_KEY`: API key is invalid
- `VALIDATION_ERROR`: Invalid request data
- `JOB_NOT_FOUND`: Search job not found
- `INTERNAL_ERROR`: Unexpected server error

## Usage Examples

### Python

```python
import requests
import json
import time

API_URL = "https://api.example.com/api/v1"
API_KEY = "your-api-key"

headers = {"X-API-Key": API_KEY}

# Start a search
response = requests.post(
    f"{API_URL}/search",
    json={"username": "john_doe", "timeout": 15},
    headers=headers
)
job_id = response.json()["job_id"]
print(f"Search started with job_id: {job_id}")

# Poll for results
while True:
    response = requests.get(
        f"{API_URL}/search/{job_id}",
        headers=headers
    )
    data = response.json()
    print(f"Status: {data['status']}, Progress: {data['progress']}%")
    
    if data['status'] in ['completed', 'failed', 'cancelled']:
        print(f"Results: {json.dumps(data['results'], indent=2)}")
        break
    
    time.sleep(1)
```

### JavaScript/Node.js

```javascript
const API_URL = 'https://api.example.com/api/v1';
const API_KEY = 'your-api-key';

// Start a search
const startSearch = async (username) => {
  const response = await fetch(`${API_URL}/search`, {
    method: 'POST',
    headers: {
      'X-API-Key': API_KEY,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ username, timeout: 15 })
  });
  return response.json();
};

// Poll for results
const getResults = async (jobId) => {
  const response = await fetch(`${API_URL}/search/${jobId}`, {
    headers: { 'X-API-Key': API_KEY }
  });
  return response.json();
};

// Stream progress with SSE
const streamProgress = (jobId, onUpdate, onComplete) => {
  const eventSource = new EventSource(`${API_URL}/search/${jobId}/status?api_key=${API_KEY}`);
  
  eventSource.addEventListener('status_update', (event) => {
    const data = JSON.parse(event.data);
    onUpdate(data);
  });
  
  eventSource.addEventListener('result', (event) => {
    const result = JSON.parse(event.data);
    console.log(`Found on ${result.site}: ${result.url}`);
  });
  
  eventSource.addEventListener('completed', (event) => {
    const data = JSON.parse(event.data);
    onComplete(data);
    eventSource.close();
  });
};

// Usage
(async () => {
  const { job_id } = await startSearch('john_doe');
  console.log(`Search started: ${job_id}`);
  
  streamProgress(job_id,
    (status) => console.log(`Progress: ${status.progress}%`),
    (results) => console.log(`Completed with ${results.results_count} results`)
  );
})();
```

### cURL

```bash
# Health check
curl https://api.example.com/api/v1/health

# Start a search
curl -X POST https://api.example.com/api/v1/search \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"username":"john_doe","timeout":15}'

# Get results
curl -H "X-API-Key: your-api-key" \
  https://api.example.com/api/v1/search/550e8400-e29b-41d4-a716-446655440000

# Stream progress (requires `curl` with EventSource support or `jq`)
curl -H "X-API-Key: your-api-key" \
  https://api.example.com/api/v1/search/550e8400-e29b-41d4-a716-446655440000/status

# Cancel a search
curl -X DELETE -H "X-API-Key: your-api-key" \
  https://api.example.com/api/v1/search/550e8400-e29b-41d4-a716-446655440000
```

## Rate Limiting

Currently, the API does not implement rate limiting, but this may be added in future versions. Plan your integrations accordingly.

## Best Practices

1. **Use API Keys Securely**: Never expose API keys in client-side code
2. **Set Appropriate Timeouts**: Adjust timeout based on your needs (default: 10 seconds)
3. **Handle Retries**: Use appropriate retry logic for failed requests
4. **Stream Progress**: Use SSE for real-time progress instead of polling
5. **Clean Up**: Cancel searches that are no longer needed

## Deployment

### Docker

Set the API keys environment variable when running the container:
```bash
docker run -e MAIGRET_API_KEYS="key1,key2" -p 5000:5000 maigret
```

### Environment Variables

- `MAIGRET_API_KEYS`: Comma-separated list of valid API keys
- `FLASK_DEBUG`: Set to `true` for debug mode (development only)
- `FLASK_HOST`: Host to bind to (default: 127.0.0.1)
- `FLASK_PORT`: Port to bind to (default: 5000)

## Support

For issues, questions, or contributions, visit the [Maigret GitHub repository](https://github.com/soxoj/maigret).
