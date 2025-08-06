# RCSB PDB ChatBot - Git-Based Deployment Guide

This guide provides a simple and efficient way to deploy and manage the RCSB PDB ChatBot using Git for easy updates and maintenance.

## 🎯 **Why Git-Based Deployment?**

- ✅ **Simple Updates**: Just `git pull` to get latest changes
- ✅ **Version Control**: Track exactly what's deployed in production
- ✅ **No File Transfers**: No need to create/upload zip files
- ✅ **Rollback Support**: Easy to revert to previous versions
- ✅ **Team Collaboration**: Multiple developers can push updates

## 📋 **Prerequisites**

### Production Server Requirements
- Ubuntu 20.04+ server with SSH access
- Docker and Docker Compose installed
- Git installed (script will install if missing)
- Port 3002 available

### Repository Information
- **Repository**: https://github.com/vivek8031/RCSB_PDB_ChatBot (Public)
- **Default Branch**: main
- **Production Directory**: `/home/ubuntu/RCSB_PDB_ChatBot`

## 🚀 **Initial Production Setup (First Time)**

### Step 1: Run Initial Deployment

From your local machine, run the automated deployment script:

```bash
./deploy-git.sh
```

**What this script does:**
1. ✅ Tests SSH connection to production server
2. ✅ Installs Git if not present
3. ✅ Verifies Docker installation
4. ✅ Clones the repository from GitHub
5. ✅ Creates user_data directory
6. ✅ Stops any existing containers
7. ✅ Builds and starts the Docker container
8. ✅ Verifies deployment with health checks
9. ✅ Shows container status and logs

### Step 2: Verify Deployment

After the script completes, verify the application is running:

```bash
# Check health endpoint
curl http://128.6.158.52:3002/_stcore/health
# Expected response: "ok"

# Check application access
curl -I http://128.6.158.52:3002
# Expected: HTTP/1.1 200 OK
```

## 🔄 **Making Updates to Production**

### Method 1: Quick Update Script (Recommended)

After making changes locally and pushing to GitHub:

```bash
# 1. Push your changes to GitHub
git add .
git commit -m "Your update message"
git push origin main

# 2. Update production server
./update-production.sh
```

**The update script automatically:**
- Pulls latest code from GitHub
- Shows version changes
- Rebuilds and restarts the container
- Verifies the update was successful

### Method 2: Manual Update Process

```bash
# Connect to production server
ssh ubuntu@128.6.158.52

# Navigate to application directory
cd /home/ubuntu/RCSB_PDB_ChatBot

# Pull latest changes
git pull origin main

# Restart application with new code
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Verify update
curl -f http://localhost:3002/_stcore/health
```

## 📊 **Complete Workflow Example**

### Scenario: Adding a New Feature

#### Step 1: Develop Locally
```bash
# Make your changes in local development
# Test locally with:
streamlit run rcsb_pdb_chatbot.py
```

#### Step 2: Commit and Push
```bash
git add .
git commit -m "✨ Add new chat export feature"
git push origin main
```

#### Step 3: Deploy to Production
```bash
./update-production.sh
```

#### Step 4: Verify in Production
```bash
# Check application is running
ssh ubuntu@128.6.158.52 "curl -f http://localhost:3002/_stcore/health"

# Check logs if needed
ssh ubuntu@128.6.158.52 "cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose logs -f"
```

## 🛠️ **Management Commands**

### Essential Commands

```bash
# Check application status
ssh ubuntu@128.6.158.52 "cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose ps"

# View real-time logs
ssh ubuntu@128.6.158.52 "cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose logs -f"

# Restart application
ssh ubuntu@128.6.158.52 "cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose restart"

# Stop application
ssh ubuntu@128.6.158.52 "cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose down"

# Start application
ssh ubuntu@128.6.158.52 "cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose up -d"
```

### Git Management

```bash
# Check current production version
ssh ubuntu@128.6.158.52 "cd /home/ubuntu/RCSB_PDB_ChatBot && git log --oneline -5"

# Check Git status
ssh ubuntu@128.6.158.52 "cd /home/ubuntu/RCSB_PDB_ChatBot && git status"

# Force update to latest (overwrites any local changes)
ssh ubuntu@128.6.158.52 "cd /home/ubuntu/RCSB_PDB_ChatBot && git reset --hard origin/main"
```

### Container Management

```bash
# View container resource usage
ssh ubuntu@128.6.158.52 "docker stats rcsb_pdb_chatbot --no-stream"

# Access container shell (for debugging)
ssh ubuntu@128.6.158.52 "docker exec -it rcsb_pdb_chatbot /bin/bash"

# View container details
ssh ubuntu@128.6.158.52 "docker inspect rcsb_pdb_chatbot"
```

## 🔧 **Configuration Management**

### Environment Variables

Your `.env` file contains production configuration:

```env
# RAGFlow Configuration
RAGFLOW_API_KEY=your_production_api_key
RAGFLOW_BASE_URL=http://127.0.0.1:9380
RAGFLOW_ASSISTANT_NAME=RCSB ChatBot v2

# Application Configuration
USER_DATA_DIR=user_data
DEBUG_MODE=false
LOG_LEVEL=INFO
```

**Important**: The `.env` file is already on your production server and should not be overwritten by Git updates.

### User Data Persistence

User session data is stored in `/home/ubuntu/RCSB_PDB_ChatBot/user_data/` and persists across updates and container restarts.

## 🚨 **Troubleshooting Common Issues**

### Issue: Git Pull Fails

**Error**: `Your local changes to the following files would be overwritten by merge`

**Solution**:
```bash
ssh ubuntu@128.6.158.52 "cd /home/ubuntu/RCSB_PDB_ChatBot && git reset --hard origin/main"
```

### Issue: Container Won't Start

**Diagnosis**:
```bash
ssh ubuntu@128.6.158.52 "cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose logs"
```

**Common Solutions**:
```bash
# Rebuild container completely
ssh ubuntu@128.6.158.52 "
    cd /home/ubuntu/RCSB_PDB_ChatBot &&
    docker-compose down &&
    docker system prune -f &&
    docker-compose build --no-cache &&
    docker-compose up -d
"
```

### Issue: Application Not Responding

**Check Health**:
```bash
ssh ubuntu@128.6.158.52 "curl -v http://localhost:3002/_stcore/health"
```

**Restart Application**:
```bash
ssh ubuntu@128.6.158.52 "cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose restart"
```

## 🔄 **Rollback to Previous Version**

If an update causes issues, you can easily rollback:

### Method 1: Rollback to Specific Commit

```bash
# Find the commit hash you want to rollback to
ssh ubuntu@128.6.158.52 "cd /home/ubuntu/RCSB_PDB_ChatBot && git log --oneline -10"

# Rollback to specific commit (replace COMMIT_HASH)
ssh ubuntu@128.6.158.52 "
    cd /home/ubuntu/RCSB_PDB_ChatBot &&
    git reset --hard COMMIT_HASH &&
    docker-compose down &&
    docker-compose build --no-cache &&
    docker-compose up -d
"
```

### Method 2: Rollback to Previous Working Version

```bash
# Rollback one commit
ssh ubuntu@128.6.158.52 "
    cd /home/ubuntu/RCSB_PDB_ChatBot &&
    git reset --hard HEAD~1 &&
    docker-compose restart
"
```

## 🔐 **Security Considerations**

### Repository Security
- ✅ **Public Repository**: Safe for open source deployment
- ✅ **No Secrets**: `.env` file not committed to Git
- ✅ **Production Isolation**: Production `.env` stays on server

### Server Security
- ✅ **SSH Key Access**: Use SSH keys instead of passwords
- ✅ **Firewall Rules**: Only necessary ports open
- ✅ **Container Isolation**: Application runs in isolated container

## 📈 **Monitoring & Maintenance**

### Regular Health Checks

Create a simple monitoring script:

```bash
#!/bin/bash
# save as check-health.sh
HEALTH_URL="http://128.6.158.52:3002/_stcore/health"
if curl -f $HEALTH_URL > /dev/null 2>&1; then
    echo "✅ Application is healthy"
else
    echo "❌ Application health check failed"
    # Add notification logic here (email, Slack, etc.)
fi
```

### Log Monitoring

```bash
# Monitor errors in real-time
ssh ubuntu@128.6.158.52 "cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose logs -f | grep -i error"

# Check recent application activity
ssh ubuntu@128.6.158.52 "cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose logs --tail=50 | grep -E '(INFO|ERROR|WARNING)'"
```

## 🎯 **Best Practices**

### Development Workflow
1. **Develop Locally**: Test changes on your local machine first
2. **Commit Frequently**: Make small, focused commits
3. **Descriptive Messages**: Use clear commit messages
4. **Test Before Deploy**: Verify changes work locally
5. **Monitor After Deploy**: Check logs after production updates

### Deployment Safety
1. **Backup User Data**: Regularly backup the user_data directory
2. **Test Health Checks**: Always verify deployment with health endpoint
3. **Monitor Logs**: Check logs immediately after deployment
4. **Have Rollback Plan**: Know how to quickly revert if needed

### Performance Optimization
1. **Log Rotation**: Implement log rotation to prevent disk space issues
2. **Container Resources**: Monitor memory and CPU usage
3. **User Data Cleanup**: Periodically clean up old session data if needed

## 📚 **Quick Reference Commands**

```bash
# Complete development to production workflow
git add . && git commit -m "Your changes" && git push origin main && ./update-production.sh

# Emergency restart
ssh ubuntu@128.6.158.52 "cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose restart"

# Check everything is working
ssh ubuntu@128.6.158.52 "cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose ps && curl -f http://localhost:3002/_stcore/health"

# View recent logs
ssh ubuntu@128.6.158.52 "cd /home/ubuntu/RCSB_PDB_ChatBot && docker-compose logs --tail=20"
```

---

## 🎉 **Summary**

With this Git-based deployment workflow:

- ✅ **Simple**: Just push to Git and run update script
- ✅ **Fast**: Updates take 30-60 seconds
- ✅ **Safe**: Easy rollback if something goes wrong  
- ✅ **Trackable**: See exactly what version is deployed
- ✅ **Collaborative**: Multiple developers can deploy updates

**Key Files:**
- `deploy-git.sh` - Initial deployment script
- `update-production.sh` - Quick update script
- `GIT-DEPLOYMENT.md` - This documentation

**Production Details:**
- **Server**: ubuntu@128.6.158.52
- **Application URL**: http://128.6.158.52:3002
- **Repository**: https://github.com/vivek8031/RCSB_PDB_ChatBot
- **Container**: rcsb_pdb_chatbot

Ready to deploy! 🚀