#!/bin/bash

# RCSB PDB ChatBot - Git-Based Production Deployment Script
# Simple and efficient deployment using public GitHub repository

set -e  # Exit on any error

# Configuration
PROD_SERVER="ubuntu@128.6.158.52"
REPO_URL="https://github.com/vivek8031/RCSB_PDB_ChatBot.git"
APP_DIR="/home/ubuntu/RCSB_PDB_ChatBot"
CONTAINER_NAME="rcsb_pdb_chatbot"

echo "🚀 Starting Git-Based RCSB PDB ChatBot Deployment..."

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

# Step 2: Check if Git is installed
print_status "Checking Git installation on production server..."
if run_remote "git --version"; then
    print_success "Git is installed"
else
    print_warning "Installing Git..."
    run_remote "sudo apt-get update && sudo apt-get install -y git"
    print_success "Git installation completed"
fi

# Step 3: Check if Docker is installed
print_status "Checking Docker installation on production server..."
if run_remote "docker --version && docker-compose --version"; then
    print_success "Docker and Docker Compose are installed"
else
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Step 4: Clone or update repository
print_status "Setting up application code from Git repository..."
run_remote "
    if [ -d '$APP_DIR' ]; then
        echo 'Repository exists, updating from Git...'
        cd $APP_DIR
        git fetch origin
        git reset --hard origin/main
        git clean -fd
        echo 'Repository updated successfully'
    else
        echo 'Cloning repository from GitHub...'
        git clone $REPO_URL $APP_DIR
        echo 'Repository cloned successfully'
    fi
"
print_success "Application code updated from Git"

# Step 5: Ensure user_data directory exists
print_status "Setting up user data directory..."
run_remote "mkdir -p $APP_DIR/user_data"
print_success "User data directory ready"

# Step 6: Stop existing container if running
print_status "Stopping existing container..."
run_remote "
    cd $APP_DIR &&
    docker-compose down || true &&
    docker stop $CONTAINER_NAME || true &&
    docker rm $CONTAINER_NAME || true
"
print_success "Existing container stopped"

# Step 7: Build and start new container
print_status "Building and starting new container..."
run_remote "
    cd $APP_DIR &&
    docker-compose build --no-cache &&
    docker-compose up -d
"
print_success "New container started"

# Step 8: Verify deployment
print_status "Verifying deployment..."
sleep 15  # Wait for container to fully start

if run_remote "curl -f http://localhost:3002/_stcore/health"; then
    print_success "Health check passed - Application is running on port 3002"
else
    print_error "Health check failed - Application may not be running correctly"
    run_remote "cd $APP_DIR && docker-compose logs --tail=50"
    exit 1
fi

# Step 9: Show container status and logs
print_status "Container status:"
run_remote "cd $APP_DIR && docker-compose ps"

print_status "Recent logs:"
run_remote "cd $APP_DIR && docker-compose logs --tail=20"

# Step 10: Show Git information
print_status "Deployed version information:"
run_remote "cd $APP_DIR && git log --oneline -5"

print_success "🎉 Git-based deployment completed successfully!"
print_status "Application is now running on:"
print_status "  - Internal: http://localhost:3002"
print_status "  - External: http://128.6.158.52 (via HAProxy)"
print_status ""
print_status "Management commands:"
print_status "  - Monitor logs: ssh $PROD_SERVER 'cd $APP_DIR && docker-compose logs -f'"
print_status "  - Restart app: ssh $PROD_SERVER 'cd $APP_DIR && docker-compose restart'"
print_status "  - Update code: ssh $PROD_SERVER 'cd $APP_DIR && git pull origin main && docker-compose restart'"
print_status "  - Stop app: ssh $PROD_SERVER 'cd $APP_DIR && docker-compose down'"

echo "✅ RCSB PDB ChatBot is now live in production with Git-based deployment!"