# RCSB PDB ChatBot - Universal Deployment Guide

Deploy anywhere with Docker - no server-specific configurations needed.

## 🚀 Quick Start (Any Server)

### 1. Clone Repository
```bash
git clone https://github.com/vivek8031/RCSB_PDB_ChatBot.git
cd RCSB_PDB_ChatBot
```

### 2. Configure Environment
```bash
# Copy and edit configuration
cp .env.example .env
nano .env  # or vim, code, etc.
```

**Required Settings:**
```bash
RAGFLOW_API_KEY=your-ragflow-api-key-here
RAGFLOW_BASE_URL=http://your-ragflow-server:9380
```

### 3. Deploy
```bash
# One command deployment
./deploy.sh
```

**That's it!** Your app is running at `http://localhost:8501`

## 🔧 Configuration Options

### Application Settings
```bash
# .env file
APP_PORT=8501              # Change port if needed
APP_HOST=0.0.0.0          # 0.0.0.0 for external access
USER_DATA_DIR=./user_data  # Data storage location
```

### Custom Port Example
```bash
# To run on port 3000
echo "APP_PORT=3000" >> .env
./deploy.sh
# Access at http://localhost:3000
```

## 🐳 Manual Docker Commands

If you prefer manual control:

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Update code
git pull
docker-compose up -d --build
```

## 🌐 Platform-Specific Notes

### Local Development
```bash
# Option 1: Docker (recommended)
./deploy.sh

# Option 2: Direct Python
cp .env.example .env
pip install -r requirements.txt
streamlit run src/rcsb_pdb_chatbot.py
```

### Cloud Deployment (AWS/Azure/GCP)
```bash
# Same commands work on any cloud VM
git clone <repo>
cd RCSB_PDB_ChatBot
cp .env.example .env
# Edit .env with your settings
./deploy.sh
```

### VPS/Dedicated Servers
```bash
# Works on Ubuntu, CentOS, Debian, etc.
# Just needs Docker installed
sudo apt update && sudo apt install docker.io docker-compose -y
git clone <repo>
cd RCSB_PDB_ChatBot
./deploy.sh
```

## 🔍 Health Check

Check if your deployment is working:

```bash
# Health endpoint
curl http://localhost:8501/_stcore/health

# If port changed
curl http://localhost:${APP_PORT}/_stcore/health
```

## 📊 Management Commands

```bash
# View application logs
docker-compose logs -f

# Restart application
docker-compose restart

# Stop application  
docker-compose down

# Update application
git pull
docker-compose up -d --build

# Clean rebuild
docker-compose down
docker-compose up -d --build --force-recreate
```

## 🚨 Troubleshooting

### Port Already in Use
```bash
# Change port in .env
echo "APP_PORT=8502" >> .env
./deploy.sh
```

### Docker Issues
```bash
# Check Docker installation
docker --version
docker-compose --version

# Fix permissions (Linux)
sudo usermod -aG docker $USER
# Log out and back in
```

### RAGFlow Connection
```bash
# Test RAGFlow connectivity
curl http://your-ragflow-server:9380/health

# Check logs for connection errors
docker-compose logs | grep -i ragflow
```

### Data Persistence
```bash
# Check user data directory
ls -la user_data/

# Backup user data
cp -r user_data/ user_data_backup/
```

## 🔒 Production Considerations

### Security
- Use environment variables for sensitive data
- Don't commit `.env` file to version control
- Consider using Docker secrets for production
- Set up HTTPS with reverse proxy (nginx/traefik)

### Performance
- Adjust container resources if needed
- Monitor user_data directory size
- Regular log rotation
- Consider persistent volume for cloud deployments

### Updates
```bash
# Safe update process
docker-compose logs > logs_backup.txt  # backup logs
cp -r user_data/ user_data_backup/     # backup data
git pull                               # update code
docker-compose up -d --build          # deploy update
```

## 📋 Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_PORT` | 8501 | Application port |
| `APP_HOST` | 0.0.0.0 | Host binding |
| `RAGFLOW_API_KEY` | - | RAGFlow API key (required) |
| `RAGFLOW_BASE_URL` | http://127.0.0.1:9380 | RAGFlow server URL |
| `RAGFLOW_ASSISTANT_NAME` | RCSB ChatBot v2 | Assistant name |
| `USER_DATA_DIR` | ./user_data | Data storage path |
| `DEBUG_MODE` | false | Debug mode |
| `LOG_LEVEL` | INFO | Logging level |

## ✅ Deployment Checklist

- [ ] Docker and Docker Compose installed
- [ ] Repository cloned
- [ ] `.env` file configured with API keys
- [ ] Port available (check with `netstat -tlnp | grep 8501`)
- [ ] RAGFlow server accessible
- [ ] `./deploy.sh` executed successfully
- [ ] Health check passes
- [ ] Application accessible in browser

This deployment method works identically on:
- Local development machines
- Cloud instances (AWS EC2, DigitalOcean, etc.)  
- VPS servers
- On-premises servers
- Any Linux/macOS system with Docker