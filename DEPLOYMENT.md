# RCSB PDB ChatBot - Production Deployment Guide

This document provides a complete step-by-step guide to deploy the RCSB PDB ChatBot from local development to production server using Docker.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Project Structure](#project-structure)
3. [Docker Configuration](#docker-configuration)
4. [GitHub Repository Setup](#github-repository-setup)
5. [Production Server Setup](#production-server-setup)
6. [Deployment Process](#deployment-process)
7. [Verification & Testing](#verification--testing)
8. [Management Commands](#management-commands)
9. [HAProxy Integration](#haproxy-integration)
10. [Update Process](#update-process)

## Prerequisites

### Local Development Environment
- Python 3.10+
- Git
- Docker (optional for local testing)
- GitHub CLI (`gh`) or GitHub account access

### Production Server Requirements
- Ubuntu 20.04+ server
- SSH access with sudo privileges
- Docker and Docker Compose installed
- Port 3002 available for the application
- Existing HAProxy setup (optional)

### Required Environment Variables
- `RAGFLOW_API_KEY` - Your RAGFlow API key
- `RAGFLOW_BASE_URL` - RAGFlow server URL (e.g., http://127.0.0.1:9380)
- `RAGFLOW_ASSISTANT_NAME` - Assistant name in RAGFlow
- `DEBUG_MODE` - Set to `false` for production

## Project Structure

```
RCSB_PDB_ChatBot/
├── rcsb_pdb_chatbot.py          # Main Streamlit application
├── user_session_manager.py      # Multi-user session management
├── ragflow_simple_client.py     # RAGFlow API client
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Production Docker configuration
├── docker-compose.yml          # Container orchestration
├── deploy.sh                   # Automated deployment script
├── .env                        # Environment variables (production values)
├── .env.example                # Environment template
├── .dockerignore               # Docker build context exclusions
├── user_data/                  # User session storage directory
└── README.md                   # Project documentation
```

## Docker Configuration

### 1. Dockerfile Creation

Create a production-ready Dockerfile with multi-stage build:

```dockerfile
# RCSB PDB ChatBot Production Dockerfile
# Multi-stage build for optimized production deployment

FROM python:3.10-slim as builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.10-slim

# Set working directory (required for Streamlit 1.10.0+)
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.10/site-packages/ /usr/local/lib/python3.10/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application code
COPY . .

# Create user_data directory for session storage
RUN mkdir -p user_data && chmod 755 user_data

# Expose port 3002 (matches HAProxy backend configuration)
EXPOSE 3002

# Health check for HAProxy integration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:3002/_stcore/health || exit 1

# Set environment variables for production
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_PORT=3002
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Run Streamlit app on port 3002 for HAProxy integration
ENTRYPOINT ["streamlit", "run", "rcsb_pdb_chatbot.py", \
            "--server.port=3002", \
            "--server.address=0.0.0.0", \
            "--server.headless=true", \
            "--browser.gatherUsageStats=false"]
```

### 2. Docker Compose Configuration

Create `docker-compose.yml` for easier container management:

```yaml
version: '3.8'

services:
  rcsb-pdb-chatbot:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: rcsb_pdb_chatbot
    ports:
      - "3002:3002"  # Map to port 3002 for HAProxy integration
    env_file:
      - .env  # Use existing .env file with production values
    volumes:
      - ./user_data:/app/user_data  # Persist user session data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "--fail", "http://localhost:3002/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    environment:
      - PYTHONUNBUFFERED=1
      - STREAMLIT_SERVER_PORT=3002
      - STREAMLIT_SERVER_ADDRESS=0.0.0.0
      - STREAMLIT_SERVER_HEADLESS=true
      - STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
    networks:
      - rcsb-network

networks:
  rcsb-network:
    driver: bridge

volumes:
  user_data:
    driver: local
```

### 3. Docker Ignore File

Create `.dockerignore` to optimize build context:

```
# Git
.git
.gitignore

# Python
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.pytest_cache/

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Local development
.env.local
.env.development
*.tmp
*.temp

# Documentation
README.md
docs/

# Deployment
deploy.sh
```

## GitHub Repository Setup

### 1. Create Private Repository

```bash
# Ensure GitHub CLI is authenticated
gh auth status

# Create private repository
gh repo create RCSB_PDB_ChatBot --private --description "RCSB PDB Research ChatBot - Multi-user RAGFlow-powered assistant with secure session management" --clone=false

# Add remote origin
git remote add origin https://github.com/YOUR_USERNAME/RCSB_PDB_ChatBot.git

# Push code to repository
git push -u origin main
```

### 2. Repository URL
Your repository will be available at: `https://github.com/YOUR_USERNAME/RCSB_PDB_ChatBot`

## Production Server Setup

### 1. Server Access
```bash
# Test SSH connection
ssh ubuntu@YOUR_SERVER_IP "echo 'SSH connection successful' && whoami && pwd && uname -a"
```

### 2. Install Dependencies

```bash
# Connect to production server
ssh ubuntu@YOUR_SERVER_IP

# Update system packages
sudo apt-get update

# Install Docker if not present
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install unzip utility
sudo apt-get install -y unzip

# Verify installations
docker --version
docker-compose --version
```

## Deployment Process

### Method 1: Zip File Deployment (Recommended)

This method transfers files directly without requiring Git authentication on the server.

#### Step 1: Prepare Deployment Package

```bash
# Create deployment zip (excluding unnecessary files)
zip -r rcsb_chatbot_deploy.zip . -x "*.git*" "*__pycache__*" ".DS_Store" "*.tmp" "*.log" "user_data/*" "*.zip"
```

#### Step 2: Upload to Production Server

```bash
# Upload zip file
scp rcsb_chatbot_deploy.zip ubuntu@YOUR_SERVER_IP:/home/ubuntu/

# Extract on production server
ssh ubuntu@YOUR_SERVER_IP "cd /home/ubuntu && unzip -o rcsb_chatbot_deploy.zip -d RCSB_PDB_ChatBot && mkdir -p RCSB_PDB_ChatBot/user_data"
```

#### Step 3: Deploy Application

```bash
# Connect to production server
ssh ubuntu@YOUR_SERVER_IP

# Navigate to application directory
cd /home/ubuntu/RCSB_PDB_ChatBot

# Stop any existing containers
docker-compose down || true

# Build Docker image
docker-compose build --no-cache

# Start application
docker-compose up -d
```

### Method 2: Git Clone Deployment (Alternative)

If you prefer using Git directly on the server:

```bash
# On production server
ssh ubuntu@YOUR_SERVER_IP

# Clone repository (requires authentication)
git clone https://github.com/YOUR_USERNAME/RCSB_PDB_ChatBot.git
cd RCSB_PDB_ChatBot

# Create user_data directory
mkdir -p user_data

# Deploy using docker-compose
docker-compose build --no-cache
docker-compose up -d
```

## Verification & Testing

### 1. Container Status Check

```bash
# Check container status
ssh ubuntu@YOUR_SERVER_IP "cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose ps"

# Expected output:
# NAME                IMAGE                               COMMAND                  SERVICE             CREATED             STATUS                   PORTS
# rcsb_pdb_chatbot    rcsb_pdb_chatbot-rcsb-pdb-chatbot   "streamlit run rcsb_…"   rcsb-pdb-chatbot    X seconds ago       Up X seconds (healthy)   0.0.0.0:3002->3002/tcp
```

### 2. Health Check Verification

```bash
# Test health endpoint
ssh ubuntu@YOUR_SERVER_IP "curl -f http://localhost:3002/_stcore/health"

# Expected output: "ok"
```

### 3. Application Access Test

```bash
# Test application homepage
ssh ubuntu@YOUR_SERVER_IP "curl -I http://localhost:3002"

# Expected: HTTP/1.1 200 OK
```

### 4. View Application Logs

```bash
# View recent logs
ssh ubuntu@YOUR_SERVER_IP "cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose logs --tail=20"

# Follow logs in real-time
ssh ubuntu@YOUR_SERVER_IP "cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose logs -f"
```

## Management Commands

### Container Management

```bash
# Check status
ssh ubuntu@YOUR_SERVER_IP 'cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose ps'

# View logs
ssh ubuntu@YOUR_SERVER_IP 'cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose logs -f'

# Restart application
ssh ubuntu@YOUR_SERVER_IP 'cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose restart'

# Stop application
ssh ubuntu@YOUR_SERVER_IP 'cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose down'

# Start application
ssh ubuntu@YOUR_SERVER_IP 'cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose up -d'

# Rebuild and restart
ssh ubuntu@YOUR_SERVER_IP 'cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose down && docker-compose build --no-cache && docker-compose up -d'
```

### System Monitoring

```bash
# Check Docker system status
ssh ubuntu@YOUR_SERVER_IP 'docker system df'

# Check Docker resource usage
ssh ubuntu@YOUR_SERVER_IP 'docker stats rcsb_pdb_chatbot'

# Check server resources
ssh ubuntu@YOUR_SERVER_IP 'free -h && df -h && top -bn1 | head -20'
```

## HAProxy Integration

The application is configured to run on port 3002, which matches typical HAProxy backend configurations.

### HAProxy Configuration Example

```
backend app1
    server app1 127.0.0.1:3002 check
```

### Health Check Configuration

The application provides a health endpoint at `/_stcore/health` that returns "ok" when the service is running properly. This can be used for HAProxy health checks:

```
backend app1
    option httpchk GET /_stcore/health
    server app1 127.0.0.1:3002 check
```

### Access Points

- **Internal Access**: `http://localhost:3002` (on production server)
- **External Access**: `http://YOUR_SERVER_IP` (via HAProxy on port 80/443)

## Update Process

### 1. Update Local Code

```bash
# Make your changes locally
# Commit changes
git add .
git commit -m "Your update message"
git push origin main
```

### 2. Deploy Updates to Production

```bash
# Method 1: Zip deployment
zip -r rcsb_chatbot_deploy_updated.zip . -x "*.git*" "*__pycache__*" ".DS_Store" "*.tmp" "*.log" "user_data/*" "*.zip"
scp rcsb_chatbot_deploy_updated.zip ubuntu@YOUR_SERVER_IP:/home/ubuntu/

# Extract and deploy
ssh ubuntu@YOUR_SERVER_IP "
    cd /home/ubuntu && 
    rm -rf RCSB_PDB_ChatBot_backup && 
    mv RCSB_PDB_ChatBot RCSB_PDB_ChatBot_backup &&
    unzip -o rcsb_chatbot_deploy_updated.zip -d RCSB_PDB_ChatBot &&
    cp RCSB_PDB_ChatBot_backup/user_data/* RCSB_PDB_ChatBot/user_data/ 2>/dev/null || true &&
    cd RCSB_PDB_ChatBot &&
    docker-compose down &&
    docker-compose build --no-cache &&
    docker-compose up -d
"
```

### 3. Verify Update

```bash
# Check application status
ssh ubuntu@YOUR_SERVER_IP "cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose ps && docker-compose logs --tail=10"
```

## Environment Variables

Ensure your `.env` file contains the following production values:

```env
# RAGFlow Configuration
RAGFLOW_API_KEY=your_production_api_key_here
RAGFLOW_BASE_URL=http://127.0.0.1:9380
RAGFLOW_ASSISTANT_NAME=RCSB ChatBot v2

# Application Configuration
USER_DATA_DIR=user_data

# Production Settings
DEBUG_MODE=false
LOG_LEVEL=INFO
```

## Security Considerations

1. **Environment Variables**: Never commit production `.env` file to Git
2. **SSH Access**: Use SSH keys instead of passwords for server access
3. **Container Security**: Application runs as non-root user in container
4. **Network Security**: Application only exposed on localhost:3002 internally
5. **Data Persistence**: User data stored in persistent Docker volume

## Backup & Recovery

### User Data Backup

```bash
# Backup user session data
ssh ubuntu@YOUR_SERVER_IP "cd /home/ubuntu/RCSB_PDB_ChatBot && tar -czf user_data_backup_$(date +%Y%m%d_%H%M%S).tar.gz user_data/"

# Download backup locally
scp ubuntu@YOUR_SERVER_IP:/home/ubuntu/RCSB_PDB_ChatBot/user_data_backup_*.tar.gz ./backups/
```

### Application Recovery

```bash
# If deployment fails, restore from backup
ssh ubuntu@YOUR_SERVER_IP "
    cd /home/ubuntu &&
    docker-compose -f RCSB_PDB_ChatBot/docker-compose.yml down || true &&
    rm -rf RCSB_PDB_ChatBot &&
    mv RCSB_PDB_ChatBot_backup RCSB_PDB_ChatBot &&
    cd RCSB_PDB_ChatBot &&
    docker-compose up -d
"
```

## Performance Optimization

### Container Resource Limits

Add resource limits to `docker-compose.yml`:

```yaml
services:
  rcsb-pdb-chatbot:
    # ... other configuration
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

### Log Rotation

Configure log rotation to prevent disk space issues:

```bash
# Add to docker-compose.yml
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "5"
```

---

## Summary

This deployment guide provides a complete process for deploying the RCSB PDB ChatBot from development to production. The containerized approach ensures consistency across environments and simplifies management operations.

**Key Benefits:**
- ✅ Production-ready Docker configuration
- ✅ Multi-user session management
- ✅ HAProxy integration support
- ✅ Health monitoring and checks
- ✅ Easy updates and rollbacks
- ✅ Persistent user data storage

For troubleshooting common issues, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).