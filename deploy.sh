#!/bin/bash

# RCSB PDB ChatBot Production Deployment Script
# Deploys the application to production server with HAProxy integration

set -e  # Exit on any error

# Configuration
PROD_SERVER="ubuntu@128.6.158.52"
REPO_URL="git@github.com:vivek8031/RCSB_PDB_ChatBot.git"
APP_DIR="/home/ubuntu/RCSB_PDB_ChatBot"
CONTAINER_NAME="rcsb_pdb_chatbot"

echo "🚀 Starting RCSB PDB ChatBot Production Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to run commands on remote server
run_remote() {
    ssh -o StrictHostKeyChecking=no $PROD_SERVER "$1"
}

# Step 1: Test SSH connection
print_status "Testing SSH connection to production server..."
if run_remote "echo 'SSH connection successful'"; then
    print_success "SSH connection established"
else
    print_error "Failed to connect to production server"
    exit 1
fi

# Step 2: Check if Docker is installed
print_status "Checking Docker installation on production server..."
if run_remote "docker --version && docker-compose --version"; then
    print_success "Docker and Docker Compose are installed"
else
    print_warning "Installing Docker and Docker Compose..."
    run_remote "
        sudo apt-get update &&
        sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common &&
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg &&
        echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \$(lsb_release -cs) stable' | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null &&
        sudo apt-get update &&
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin &&
        sudo usermod -aG docker ubuntu &&
        sudo curl -L \"https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose &&
        sudo chmod +x /usr/local/bin/docker-compose
    "
    print_success "Docker installation completed"
fi

# Step 3: Clone or update repository
print_status "Setting up application code..."
run_remote "
    if [ -d '$APP_DIR' ]; then
        echo 'Repository exists, updating...'
        cd $APP_DIR && git pull origin main
    else
        echo 'Cloning repository...'
        git clone $REPO_URL $APP_DIR
    fi
"
print_success "Application code updated"

# Step 4: Copy .env file to production server
print_status "Copying environment configuration..."
scp -o StrictHostKeyChecking=no .env $PROD_SERVER:$APP_DIR/
print_success "Environment configuration copied"

# Step 5: Stop existing container if running
print_status "Stopping existing container..."
run_remote "
    cd $APP_DIR &&
    docker-compose down || true &&
    docker stop $CONTAINER_NAME || true &&
    docker rm $CONTAINER_NAME || true
"
print_success "Existing container stopped"

# Step 6: Build and start new container
print_status "Building and starting new container..."
run_remote "
    cd $APP_DIR &&
    docker-compose build --no-cache &&
    docker-compose up -d
"
print_success "New container started"

# Step 7: Verify deployment
print_status "Verifying deployment..."
sleep 10  # Wait for container to start

if run_remote "curl -f http://localhost:3002/_stcore/health"; then
    print_success "Health check passed - Application is running on port 3002"
else
    print_error "Health check failed - Application may not be running correctly"
    run_remote "cd $APP_DIR && docker-compose logs --tail=50"
    exit 1
fi

# Step 8: Check container status
print_status "Container status:"
run_remote "cd $APP_DIR && docker-compose ps"

# Step 9: Show logs
print_status "Recent logs:"
run_remote "cd $APP_DIR && docker-compose logs --tail=20"

print_success "🎉 Deployment completed successfully!"
print_status "Application is now running on:"
print_status "  - Internal: http://localhost:3002"
print_status "  - External: http://128.6.158.52 (via HAProxy)"
print_status ""
print_status "To monitor logs: ssh $PROD_SERVER 'cd $APP_DIR && docker-compose logs -f'"
print_status "To restart: ssh $PROD_SERVER 'cd $APP_DIR && docker-compose restart'"
print_status "To stop: ssh $PROD_SERVER 'cd $APP_DIR && docker-compose down'"

echo "✅ RCSB PDB ChatBot is now live in production!"