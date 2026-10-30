# REST API Deployment Guide

This guide covers deploying the Maigret REST API in various environments.

## Quick Start (Local Development)

```bash
# Install Maigret
pip install maigret

# Set API keys
export MAIGRET_API_KEYS="your-api-key-here"

# Start the API server
python -m maigret.web.app
```

The API will be available at `http://localhost:5000/api/v1`

## Environment Configuration

### API Keys

Set one or more API keys for authentication:

```bash
export MAIGRET_API_KEYS="key1,key2,key3"
```

In production, store API keys securely (e.g., in environment variables managed by your deployment system).

### API Configuration

Control API behavior via environment variables:

```bash
# Enable/disable the API (default: true)
export MAIGRET_API_ENABLED=true

# Maximum number of concurrent jobs (default: 1000)
export MAIGRET_API_MAX_JOBS=500

# Job retention time in seconds (default: 3600, i.e., 1 hour)
export MAIGRET_API_JOB_TTL=3600

# Enable rate limiting (default: false)
export MAIGRET_API_RATE_LIMITING=true

# Rate limit: requests per minute per API key (default: 60)
export MAIGRET_API_RATE_LIMIT=60

# Default request timeout in seconds (default: 10)
export MAIGRET_API_TIMEOUT=10

# Default number of retries (default: 1)
export MAIGRET_API_RETRIES=2
```

### Flask Configuration

```bash
# Debug mode (development only, never use in production)
export FLASK_DEBUG=false

# Host to bind to (default: 127.0.0.1)
export FLASK_HOST=0.0.0.0

# Port to bind to (default: 5000)
export FLASK_PORT=5000

# Secret key for sessions (auto-generated if not set)
export FLASK_SECRET_KEY=your-secret-key-here
```

## Deployment Methods

### Docker

#### Docker Image (if available)

```bash
docker run \
  -e MAIGRET_API_KEYS="your-api-key" \
  -p 5000:5000 \
  soxoj/maigret:latest
```

#### Docker Compose

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  maigret-api:
    image: soxoj/maigret:latest
    environment:
      MAIGRET_API_KEYS: "your-api-key"
      FLASK_HOST: "0.0.0.0"
      FLASK_PORT: "5000"
    ports:
      - "5000:5000"
    volumes:
      - ./reports:/app/reports  # Optional: persist reports
```

Run with:
```bash
docker-compose up -d
```

#### Building Your Own Image

```dockerfile
FROM python:3.10-slim

WORKDIR /app

RUN pip install maigret

ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=5000
ENV MAIGRET_API_ENABLED=true

EXPOSE 5000

CMD ["python", "-m", "maigret.web.app"]
```

Build and run:
```bash
docker build -t my-maigret-api .
docker run -e MAIGRET_API_KEYS="your-key" -p 5000:5000 my-maigret-api
```

### Systemd Service (Linux)

Create `/etc/systemd/system/maigret-api.service`:

```ini
[Unit]
Description=Maigret OSINT API
After=network.target

[Service]
Type=simple
User=maigret
WorkingDirectory=/home/maigret/maigret
Environment="MAIGRET_API_KEYS=your-api-key"
Environment="FLASK_HOST=0.0.0.0"
Environment="FLASK_PORT=5000"
ExecStart=/usr/bin/python3 -m maigret.web.app
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable maigret-api
sudo systemctl start maigret-api
sudo systemctl status maigret-api
```

### Using Gunicorn (Production)

Install Gunicorn:
```bash
pip install gunicorn
```

Create a `run.py`:
```python
from maigret.web.app import app

if __name__ == '__main__':
    app.run()
```

Run with Gunicorn:
```bash
gunicorn \
  --workers 4 \
  --worker-class gevent \
  --bind 0.0.0.0:5000 \
  --timeout 120 \
  run:app
```

### Using uWSGI (Production)

Install uWSGI:
```bash
pip install uwsgi
```

Create `uwsgi.ini`:
```ini
[uwsgi]
module = maigret.web.app:app
master = true
processes = 4
socket = /tmp/maigret.sock
chmod-socket = 666
vacuum = true
die-on-term = true
```

Run:
```bash
uwsgi uwsgi.ini
```

### Nginx Reverse Proxy

Configure Nginx to proxy requests to the API:

```nginx
upstream maigret {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name api.example.com;

    # Redirect to HTTPS (recommended)
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    client_max_body_size 10M;
    proxy_request_buffering off;

    location /api/ {
        proxy_pass http://maigret;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # For Server-Sent Events (SSE)
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400;
    }
}
```

### Apache Reverse Proxy

Enable modules:
```bash
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod rewrite
```

Create a virtual host configuration:

```apache
<VirtualHost *:443>
    ServerName api.example.com
    
    SSLEngine on
    SSLCertificateFile /path/to/cert.pem
    SSLCertificateKeyFile /path/to/key.pem

    ProxyPreserveHost On
    ProxyPass /api/ http://127.0.0.1:5000/api/
    ProxyPassReverse /api/ http://127.0.0.1:5000/api/

    # For Server-Sent Events
    ProxyPassReverse / http://127.0.0.1:5000/
    SetEnvIf Request_URI "^/api/v1/search/.*/status$" no-proxy
    ProxyPass /api/v1/search/ http://127.0.0.1:5000/api/v1/search/ nocanon
</VirtualHost>
```

### Kubernetes

Create a Deployment manifest:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: maigret-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: maigret-api
  template:
    metadata:
      labels:
        app: maigret-api
    spec:
      containers:
      - name: maigret-api
        image: soxoj/maigret:latest
        ports:
        - containerPort: 5000
        env:
        - name: MAIGRET_API_KEYS
          valueFrom:
            secretKeyRef:
              name: maigret-api-keys
              key: keys
        - name: FLASK_HOST
          value: "0.0.0.0"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: maigret-api-service
spec:
  selector:
    app: maigret-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 5000
  type: LoadBalancer
```

Create API keys secret:
```bash
kubectl create secret generic maigret-api-keys --from-literal=keys="key1,key2"
```

Deploy:
```bash
kubectl apply -f deployment.yaml
```

## Monitoring

### Health Check

Monitor API health:
```bash
curl http://localhost:5000/api/v1/health
```

### Logs

View Flask logs:
```bash
# Development
python -m maigret.web.app  # Logs to console

# Production with Systemd
sudo journalctl -u maigret-api -f

# With Docker
docker logs -f container-id
```

### Metrics

Enable Python logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Best Practices

1. **API Keys**: Use strong, randomly generated API keys
2. **HTTPS**: Always use HTTPS in production (use Nginx/Apache with SSL)
3. **Rate Limiting**: Enable `MAIGRET_API_RATE_LIMITING` in production
4. **Firewall**: Restrict API access to trusted networks
5. **Secrets Management**: Use environment variables or secrets management systems (AWS Secrets Manager, HashiCorp Vault, etc.)
6. **Logging**: Monitor logs for suspicious activity
7. **Updates**: Keep Maigret updated for security patches

## Troubleshooting

### API Not Starting

Check if port is already in use:
```bash
lsof -i :5000
```

Change port:
```bash
export FLASK_PORT=5001
python -m maigret.web.app
```

### Authentication Errors

Verify API key is set:
```bash
echo $MAIGRET_API_KEYS
```

Test with curl:
```bash
curl -H "X-API-Key: your-key" http://localhost:5000/api/v1/health
```

### Server-Sent Events Not Working

Ensure proxy (Nginx/Apache) doesn't buffer responses. See reverse proxy configuration above.

### Memory Issues

Reduce max jobs:
```bash
export MAIGRET_API_MAX_JOBS=100
```

Reduce job TTL:
```bash
export MAIGRET_API_JOB_TTL=600  # 10 minutes instead of 1 hour
```

## Performance Tuning

### Worker Threads

With Gunicorn:
```bash
gunicorn --workers 4 --worker-class gevent --gevent-worker-class sync
```

### Connection Pool

Maigret uses connection pooling. Tune with:
```bash
export MAIGRET_API_MAX_CONNECTIONS=100
```

### Timeout Values

Adjust based on network conditions:
```bash
export MAIGRET_API_TIMEOUT=30  # Increase for slow networks
```

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/soxoj/maigret/issues
- Documentation: https://maigret.readthedocs.io
- Community: [Discussion threads on GitHub]

