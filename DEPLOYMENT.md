# Deployment Guide

This guide covers deploying the Email Service API to production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Deployment Options](#deployment-options)
- [Docker Deployment](#docker-deployment)
- [Cloud Deployments](#cloud-deployments)
- [Monitoring](#monitoring)
- [Security Hardening](#security-hardening)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required

- Python 3.11+ (for non-Docker deployments)
- Docker and Docker Compose (for containerized deployments)
- SMTP server credentials
- SSL/TLS certificates (for HTTPS)
- Reverse proxy (Nginx, Traefik, or cloud load balancer)

### Recommended

- Domain name with DNS configured
- Monitoring tools (Prometheus, Grafana, Datadog)
- Log aggregation (ELK stack, CloudWatch)
- Secret management (Vault, AWS Secrets Manager)

## Environment Configuration

### 1. Create Production Environment File

```bash
cp .env.example .env
```

### 2. Configure Production Settings

Edit `.env` with production values:

```env
# Production Configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# CORS - Restrict to your domain
CORS_ORIGINS=["https://yourdomain.com","https://api.yourdomain.com"]

# SMTP Settings
EMAIL_PASSWORD=your_secure_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=noreply@yourdomain.com

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60
```

## Deployment Options

### Option 1: Docker Compose (Recommended)

Best for: VPS, dedicated servers, simple deployments

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Check health
curl http://localhost:8000/health
```

### Option 2: Kubernetes

Best for: Large-scale deployments, high availability

See [Kubernetes Deployment](#kubernetes-deployment) section.

### Option 3: Cloud Platforms

Best for: Managed deployments, auto-scaling

- [AWS Deployment](#aws-deployment)
- [Google Cloud Run](#google-cloud-run)
- [Azure Container Instances](#azure-container-instances)

## Docker Deployment

### Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  email-service:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: email-service-prod
    restart: always
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./email_template.html:/app/email_template.html:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
    networks:
      - email-network

  nginx:
    image: nginx:alpine
    container_name: nginx-proxy
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - email-service
    networks:
      - email-network

networks:
  email-network:
    driver: bridge
```

### Nginx Configuration

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream email_service {
        server email-service:8000;
    }

    server {
        listen 80;
        server_name api.yourdomain.com;

        # Redirect to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name api.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        location / {
            proxy_pass http://email_service;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        location /health {
            proxy_pass http://email_service/health;
            access_log off;
        }
    }
}
```

### Deploy

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Cloud Deployments

### AWS Deployment

#### Option A: AWS ECS Fargate

1. **Build and push Docker image to ECR:**

```bash
# Create ECR repository
aws ecr create-repository --repository-name email-service

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Build and tag
docker build -t email-service .
docker tag email-service:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/email-service:latest

# Push
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/email-service:latest
```

2. **Create ECS Task Definition:**

```json
{
  "family": "email-service",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "email-service",
      "image": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/email-service:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "EMAIL_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT_ID:secret:email-password"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/email-service",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

#### Option B: AWS Elastic Beanstalk

```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init -p docker email-service --region us-east-1

# Create environment
eb create production-env

# Deploy
eb deploy
```

### Google Cloud Run

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/email-service

# Deploy to Cloud Run
gcloud run deploy email-service \
  --image gcr.io/PROJECT_ID/email-service \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production \
  --set-secrets EMAIL_PASSWORD=email-password:latest \
  --port 8000 \
  --memory 512Mi \
  --timeout 60s \
  --max-instances 10
```

### Azure Container Instances

```bash
# Create resource group
az group create --name email-service-rg --location eastus

# Create container registry
az acr create --resource-group email-service-rg --name emailserviceacr --sku Basic

# Build and push
az acr build --registry emailserviceacr --image email-service:latest .

# Deploy
az container create \
  --resource-group email-service-rg \
  --name email-service \
  --image emailserviceacr.azurecr.io/email-service:latest \
  --dns-name-label email-service-unique \
  --ports 8000 \
  --environment-variables ENVIRONMENT=production \
  --secure-environment-variables EMAIL_PASSWORD=$EMAIL_PASSWORD \
  --cpu 1 \
  --memory 1
```

## Kubernetes Deployment

### 1. Create Kubernetes Manifests

**deployment.yaml:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: email-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: email-service
  template:
    metadata:
      labels:
        app: email-service
    spec:
      containers:
      - name: email-service
        image: your-registry/email-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: EMAIL_PASSWORD
          valueFrom:
            secretKeyRef:
              name: email-secrets
              key: password
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
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
  name: email-service
spec:
  selector:
    app: email-service
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

### 2. Deploy

```bash
# Create secret
kubectl create secret generic email-secrets --from-literal=password=YOUR_PASSWORD

# Apply manifests
kubectl apply -f deployment.yaml

# Check status
kubectl get pods
kubectl get services
```

## Monitoring

### Health Check Monitoring

Use monitoring tools to check `/health` endpoint:

```bash
# Simple check
curl https://api.yourdomain.com/health

# With monitoring (example: Prometheus)
# Add to prometheus.yml:
scrape_configs:
  - job_name: 'email-service'
    static_configs:
      - targets: ['email-service:8000']
    metrics_path: '/metrics'
```

### Log Aggregation

**ELK Stack Example:**

```yaml
# Add to docker-compose
filebeat:
  image: docker.elastic.co/beats/filebeat:8.0.0
  volumes:
    - /var/lib/docker/containers:/var/lib/docker/containers:ro
    - ./filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
```

### Application Monitoring

Consider integrating:
- **Sentry** for error tracking
- **DataDog** for APM
- **New Relic** for performance monitoring

## Security Hardening

### 1. Use Secrets Manager

Never store secrets in environment variables for production.

**AWS Secrets Manager:**
```python
import boto3

client = boto3.client('secretsmanager')
secret = client.get_secret_value(SecretId='email-password')
```

### 2. Network Security

- Use VPC/Private networks
- Implement security groups
- Enable WAF for API Gateway

### 3. SSL/TLS

- Use Let's Encrypt for free certificates
- Enable HSTS headers
- Use TLS 1.2+ only

### 4. Rate Limiting

For production, use distributed rate limiting:

```python
# Use Redis for rate limiting
from redis import Redis
from limits import storage
from limits.strategies import MovingWindowRateLimiter

storage_uri = "redis://localhost:6379"
storage = storage.RedisStorage(storage_uri)
limiter = MovingWindowRateLimiter(storage)
```

## Troubleshooting

### Email Not Sending

```bash
# Check logs
docker-compose logs email-service

# Test SMTP connection
telnet smtp.gmail.com 587

# Check environment variables
docker exec email-service env | grep EMAIL
```

### High Memory Usage

```bash
# Check container stats
docker stats email-service

# Adjust memory limits in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 512M
```

### Rate Limit Issues

```bash
# Check rate limit configuration
curl https://api.yourdomain.com/health

# Adjust in .env
RATE_LIMIT_REQUESTS=20
RATE_LIMIT_WINDOW=60
```

## Backup and Disaster Recovery

### 1. Configuration Backup

```bash
# Backup environment files
tar -czf config-backup-$(date +%Y%m%d).tar.gz .env email_template.html

# Store in S3
aws s3 cp config-backup-*.tar.gz s3://your-backup-bucket/
```

### 2. Rollback Strategy

```bash
# Tag each deployment
docker tag email-service:latest email-service:v1.0.0

# Rollback
docker-compose down
docker-compose up -d email-service:v0.9.0
```

## Performance Optimization

### 1. Enable Caching

Template caching is built-in. For additional caching:

```python
# Add Redis caching
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://localhost")
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
```

### 2. Connection Pooling

Already implemented in the SMTP service with retry logic.

### 3. Horizontal Scaling

Deploy multiple instances behind a load balancer:

```bash
docker-compose up -d --scale email-service=3
```

## Maintenance

### Regular Updates

```bash
# Update dependencies
pip install --upgrade -r requirements.txt

# Rebuild Docker image
docker-compose build --no-cache

# Deploy with zero downtime
docker-compose up -d --no-deps --build email-service
```

### Security Patches

Subscribe to security advisories:
- Python security mailing list
- FastAPI security updates
- Docker security notices
