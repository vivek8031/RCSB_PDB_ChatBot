#!/bin/bash

# RCSB PDB ChatBot - Quick Production Update Script
# For updating production server after making changes

set -e  # Exit on any error

# Configuration
PROD_SERVER="ubuntu@128.6.158.52"
APP_DIR="/home/ubuntu/RCSB_PDB_ChatBot"

echo "🔄 Updating RCSB PDB ChatBot in Production..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[UPDATE]${NC} $1"
}

# Function to run commands on remote server
run_remote() {
    ssh -o StrictHostKeyChecking=no $PROD_SERVER "$1"
}

# Step 1: Show current version
print_status "Current production version:"
run_remote "cd $APP_DIR && git log --oneline -1"

# Step 2: Pull latest changes
print_warning "Pulling latest changes from Git repository..."
run_remote "
    cd $APP_DIR &&
    git fetch origin &&
    git reset --hard origin/main &&
    git clean -fd
"
print_success "Code updated from Git repository"

# Step 3: Show new version
print_status "New production version:"
run_remote "cd $APP_DIR && git log --oneline -1"

# Step 4: Restart application
print_warning "Restarting application..."
run_remote "
    cd $APP_DIR &&
    docker-compose down &&
    docker-compose build --no-cache &&
    docker-compose up -d
"
print_success "Application restarted with latest code"

# Step 5: Verify update
print_status "Verifying application is running..."
sleep 10  # Wait for container to start

if run_remote "curl -f http://localhost:3002/_stcore/health"; then
    print_success "✅ Application update successful - Health check passed"
else
    echo -e "${RED}[ERROR]${NC} Health check failed after update"
    run_remote "cd $APP_DIR && docker-compose logs --tail=20"
    exit 1
fi

# Step 6: Show status
print_status "Application status:"
run_remote "cd $APP_DIR && docker-compose ps"

print_success "🎉 Production update completed successfully!"
print_status "Application is running the latest version from Git repository."