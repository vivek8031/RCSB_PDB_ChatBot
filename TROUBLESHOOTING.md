# RCSB PDB ChatBot - Troubleshooting Guide

This document covers common issues you might encounter during deployment and operation of the RCSB PDB ChatBot, along with their solutions.

## Table of Contents

1. [Docker Build Issues](#docker-build-issues)
2. [Container Runtime Issues](#container-runtime-issues)
3. [Application Issues](#application-issues)
4. [Network & Connectivity Issues](#network--connectivity-issues)
5. [Environment Variable Issues](#environment-variable-issues)
6. [Performance Issues](#performance-issues)
7. [Data Persistence Issues](#data-persistence-issues)
8. [HAProxy Integration Issues](#haproxy-integration-issues)
9. [Update & Deployment Issues](#update--deployment-issues)
10. [Monitoring & Debugging](#monitoring--debugging)

## Docker Build Issues

### Issue: Python Package Installation Fails

**Error:**
```
ERROR: Could not find a version that satisfies the requirement ragflow-sdk>=0.19.0
```

**Solution:**
Ensure you're using Python 3.10+ in the Dockerfile:

```dockerfile
FROM python:3.10-slim as builder
# and
FROM python:3.10-slim
```

**Verification:**
```bash
# Check Python version in container
docker run --rm rcsb_pdb_chatbot python --version
```

### Issue: Docker Build Context Too Large

**Error:**
```
WARN: build context is large
```

**Solution:**
1. Check `.dockerignore` is properly configured
2. Remove unnecessary files:

```bash
# Clean up before building
rm -rf __pycache__ .DS_Store *.zip user_data/*
```

### Issue: Permission Denied During Build

**Error:**
```
permission denied while trying to connect to the Docker daemon socket
```

**Solution:**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Or run with sudo (not recommended)
sudo docker-compose build
```

## Container Runtime Issues

### Issue: Container Exits Immediately

**Symptoms:**
- Container status shows "Exited (1)"
- Application not accessible

**Diagnosis:**
```bash
# Check container logs
docker-compose logs rcsb-pdb-chatbot

# Check container status
docker-compose ps
```

**Common Solutions:**

1. **Environment Variables Missing:**
```bash
# Verify .env file exists and has required variables
cat .env
```

2. **Port Conflict:**
```bash
# Check if port 3002 is already in use
sudo netstat -tlnp | grep 3002
```

3. **Permission Issues:**
```bash
# Fix user_data directory permissions
chmod 755 user_data/
```

### Issue: Container Unhealthy Status

**Symptoms:**
- Container shows as "unhealthy" in docker-compose ps
- Health check failing

**Diagnosis:**
```bash
# Test health endpoint manually
docker exec rcsb_pdb_chatbot curl -f http://localhost:3002/_stcore/health

# Check Streamlit logs
docker-compose logs rcsb-pdb-chatbot | grep -i error
```

**Solutions:**
1. Increase health check timeout in docker-compose.yml
2. Verify Streamlit is binding to correct address/port
3. Check for application startup errors

## Application Issues

### Issue: RAGFlow Connection Errors

**Error:**
```
Failed to connect to RAGFlow server
```

**Diagnosis:**
```bash
# Test RAGFlow connectivity from container
docker exec rcsb_pdb_chatbot curl -v http://127.0.0.1:9380/health

# Check environment variables
docker exec rcsb_pdb_chatbot printenv | grep RAGFLOW
```

**Solutions:**
1. Verify RAGFlow server is running
2. Check RAGFLOW_BASE_URL in .env file
3. Verify API key is correct
4. Check network connectivity between containers

### Issue: Session Data Not Persisting

**Symptoms:**
- User sessions lost after container restart
- User data directory empty

**Diagnosis:**
```bash
# Check volume mounting
docker inspect rcsb_pdb_chatbot | grep -A 10 "Mounts"

# Verify user_data directory
ls -la user_data/
```

**Solutions:**
1. Ensure user_data directory exists before container start
2. Check volume mapping in docker-compose.yml
3. Verify directory permissions

### Issue: Markdown Rendering Problems

**Symptoms:**
- Raw markdown text displayed instead of formatted content
- Code blocks not processing correctly

**Diagnosis:**
Check application logs for markdown processing errors:
```bash
docker-compose logs rcsb-pdb-chatbot | grep -i markdown
```

**Solutions:**
1. Verify process_markdown_response function is working
2. Check assistant prompt format (should wrap in ```markdown blocks)
3. Ensure Streamlit is using built-in markdown rendering

## Network & Connectivity Issues

### Issue: Application Not Accessible on Port 3002

**Symptoms:**
- Connection refused when accessing localhost:3002
- Curl timeouts

**Diagnosis:**
```bash
# Check if container is listening on port
docker exec rcsb_pdb_chatbot netstat -tlnp | grep 3002

# Check port mapping
docker port rcsb_pdb_chatbot
```

**Solutions:**
1. Verify Streamlit server.address is set to 0.0.0.0
2. Check firewall rules on production server
3. Ensure Docker port mapping is correct

### Issue: HAProxy Cannot Reach Backend

**Symptoms:**
- HAProxy shows backend server as down
- Health checks failing from HAProxy

**Diagnosis:**
```bash
# Test from HAProxy server perspective
curl -v http://127.0.0.1:3002/_stcore/health

# Check HAProxy logs
sudo tail -f /var/log/haproxy.log
```

**Solutions:**
1. Verify application is bound to all interfaces (0.0.0.0)
2. Check HAProxy backend configuration
3. Ensure health check URL is correct

## Environment Variable Issues

### Issue: Environment Variables Not Loading

**Symptoms:**
- Application using default values instead of .env values
- Configuration not taking effect

**Diagnosis:**
```bash
# Check if .env file is present
ls -la .env

# Verify environment variables in container
docker exec rcsb_pdb_chatbot printenv
```

**Solutions:**
1. Ensure .env file is in the same directory as docker-compose.yml
2. Check .env file format (no spaces around =)
3. Restart container after .env changes

### Issue: Debug Mode Active in Production

**Symptoms:**
- References showing in production
- Debug features visible to users

**Solution:**
```bash
# Verify DEBUG_MODE setting
grep DEBUG_MODE .env
# Should show: DEBUG_MODE=false

# Restart container after change
docker-compose restart
```

## Performance Issues

### Issue: High Memory Usage

**Symptoms:**
- Container consuming excessive memory
- Server becoming unresponsive

**Diagnosis:**
```bash
# Monitor container resource usage
docker stats rcsb_pdb_chatbot

# Check system memory
free -h
```

**Solutions:**
1. Add memory limits to docker-compose.yml:
```yaml
deploy:
  resources:
    limits:
      memory: 2G
```

2. Monitor user session data growth
3. Implement session cleanup if needed

### Issue: Slow Response Times

**Symptoms:**
- Application taking long time to respond
- Timeouts during user interactions

**Diagnosis:**
```bash
# Check RAGFlow response times
docker exec rcsb_pdb_chatbot curl -w "@curl-format.txt" -s -o /dev/null http://127.0.0.1:9380/api/status

# Monitor application logs for slow queries
docker-compose logs -f rcsb-pdb-chatbot
```

**Solutions:**
1. Check RAGFlow server performance
2. Optimize user session storage
3. Add caching if applicable

## Data Persistence Issues

### Issue: User Data Lost After Updates

**Symptoms:**
- User sessions disappear after deployment
- Chat history not preserved

**Prevention:**
```bash
# Always backup user data before updates
tar -czf user_data_backup_$(date +%Y%m%d_%H%M%S).tar.gz user_data/
```

**Recovery:**
```bash
# Restore from backup
tar -xzf user_data_backup_YYYYMMDD_HHMMSS.tar.gz
```

### Issue: Disk Space Issues

**Symptoms:**
- Container cannot start due to disk space
- Logs showing "no space left on device"

**Diagnosis:**
```bash
# Check disk usage
df -h
du -sh user_data/

# Check Docker disk usage
docker system df
```

**Solutions:**
1. Clean up old Docker images:
```bash
docker system prune -f
docker image prune -a -f
```

2. Implement log rotation in docker-compose.yml
3. Archive old user session data

## HAProxy Integration Issues

### Issue: 502 Bad Gateway from HAProxy

**Symptoms:**
- HAProxy returns 502 error
- Backend server appears down in HAProxy stats

**Diagnosis:**
```bash
# Check backend connectivity from HAProxy server
curl -v http://127.0.0.1:3002/

# Verify HAProxy configuration
sudo haproxy -c -f /etc/haproxy/haproxy.cfg
```

**Solutions:**
1. Ensure application is running and healthy
2. Check HAProxy backend server configuration
3. Verify network connectivity

### Issue: Health Checks Failing

**Symptoms:**
- HAProxy marks backend as unhealthy
- Intermittent 503 errors

**Solutions:**
1. Adjust health check intervals in HAProxy config
2. Increase application startup time before health checks
3. Verify health check URL path

## Update & Deployment Issues

### Issue: Deployment Fails During Update

**Symptoms:**
- Docker build fails during update
- Container won't start with new code

**Recovery Process:**
```bash
# Restore from backup
ssh ubuntu@YOUR_SERVER_IP "
    cd /home/ubuntu &&
    docker-compose -f RCSB_PDB_ChatBot/docker-compose.yml down &&
    rm -rf RCSB_PDB_ChatBot &&
    mv RCSB_PDB_ChatBot_backup RCSB_PDB_ChatBot &&
    cd RCSB_PDB_ChatBot &&
    docker-compose up -d
"
```

### Issue: File Transfer Fails

**Symptoms:**
- SCP upload interrupted
- Zip extraction fails

**Solutions:**
1. Check network connectivity
2. Verify disk space on server
3. Use rsync for more reliable transfers:
```bash
rsync -avz --progress ./rcsb_chatbot_deploy.zip ubuntu@YOUR_SERVER_IP:/home/ubuntu/
```

## Monitoring & Debugging

### Useful Monitoring Commands

```bash
# Real-time container logs
docker-compose logs -f --tail=100

# Resource monitoring
docker stats rcsb_pdb_chatbot

# Health status check
curl -s http://localhost:3002/_stcore/health

# Application status
docker-compose ps

# System resource usage
htop
```

### Debug Mode Enable (Temporary)

For troubleshooting, temporarily enable debug mode:

```bash
# Edit .env file
echo "DEBUG_MODE=true" >> .env

# Restart container
docker-compose restart

# Remember to disable after debugging
sed -i 's/DEBUG_MODE=true/DEBUG_MODE=false/' .env
docker-compose restart
```

### Log Analysis

```bash
# Search for specific errors
docker-compose logs rcsb-pdb-chatbot | grep -i "error\|exception\|failed"

# Check startup sequence
docker-compose logs rcsb-pdb-chatbot | head -50

# Monitor real-time issues
docker-compose logs -f rcsb-pdb-chatbot | grep -i "error"
```

### Container Shell Access

```bash
# Access container shell for debugging
docker exec -it rcsb_pdb_chatbot /bin/bash

# Check Python environment
docker exec rcsb_pdb_chatbot python -c "import streamlit; print(streamlit.__version__)"

# Test RAGFlow connectivity
docker exec rcsb_pdb_chatbot curl -v http://127.0.0.1:9380/health
```

## Emergency Procedures

### Complete Service Restart

```bash
# Full service restart procedure
ssh ubuntu@YOUR_SERVER_IP "
    cd /home/ubuntu/RCSB_PDB_ChatBot &&
    docker-compose down &&
    docker system prune -f &&
    docker-compose up -d
"
```

### Rollback to Previous Version

```bash
# If you have a backup directory
ssh ubuntu@YOUR_SERVER_IP "
    cd /home/ubuntu &&
    docker-compose -f RCSB_PDB_ChatBot/docker-compose.yml down &&
    mv RCSB_PDB_ChatBot RCSB_PDB_ChatBot_failed &&
    mv RCSB_PDB_ChatBot_backup RCSB_PDB_ChatBot &&
    cd RCSB_PDB_ChatBot &&
    docker-compose up -d
"
```

### Fresh Deployment

```bash
# Complete fresh deployment (will lose user data)
ssh ubuntu@YOUR_SERVER_IP "
    docker stop rcsb_pdb_chatbot || true &&
    docker rm rcsb_pdb_chatbot || true &&
    docker rmi rcsb_pdb_chatbot-rcsb-pdb-chatbot || true &&
    rm -rf /home/ubuntu/RCSB_PDB_ChatBot &&
    # Then follow normal deployment process
"
```

## Getting Help

### Log Collection for Support

```bash
# Collect all relevant logs
mkdir -p troubleshooting_logs
docker-compose logs rcsb-pdb-chatbot > troubleshooting_logs/application.log
docker inspect rcsb_pdb_chatbot > troubleshooting_logs/container_inspect.json
docker-compose config > troubleshooting_logs/compose_config.yml
docker system df > troubleshooting_logs/docker_usage.txt
df -h > troubleshooting_logs/disk_usage.txt
free -h > troubleshooting_logs/memory_usage.txt

# Create support package
tar -czf support_logs_$(date +%Y%m%d_%H%M%S).tar.gz troubleshooting_logs/
```

### Common Command Reference

```bash
# Quick health check
curl -s http://localhost:3002/_stcore/health && echo " - Health OK" || echo " - Health FAIL"

# Container status
docker-compose ps | grep rcsb_pdb_chatbot

# Recent errors
docker-compose logs rcsb-pdb-chatbot | tail -20 | grep -i error

# Resource usage
docker stats rcsb_pdb_chatbot --no-stream
```

---

## Prevention Best Practices

1. **Regular Backups**: Backup user data before any updates
2. **Monitoring**: Set up basic monitoring for container health
3. **Resource Limits**: Configure appropriate memory and CPU limits
4. **Log Rotation**: Implement log rotation to prevent disk space issues
5. **Health Checks**: Ensure health checks are properly configured
6. **Documentation**: Keep deployment documentation updated
7. **Testing**: Test updates in staging environment when possible

For deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).