#!/bin/bash
# RCSB PDB ChatBot - Server Update Script
# Updates the running container with latest code from GitHub

set -e

echo "🔄 RCSB PDB ChatBot Server Update Script"
echo "======================================="

# Check if we're in the right directory
if [[ ! -f "docker-compose.yml" ]]; then
    echo "❌ Error: docker-compose.yml not found. Please run this script from the project directory."
    exit 1
fi

echo "📥 Pulling latest changes from GitHub..."
git pull origin main

echo "🛑 Stopping current container..."
docker-compose down

echo "🔨 Rebuilding container with latest changes..."
docker-compose build --no-cache

echo "🚀 Starting updated container..."
docker-compose up -d

echo "⏳ Waiting for container to be ready..."
sleep 10

echo "🩺 Checking container health..."
if docker-compose ps | grep -q "healthy\|Up"; then
    echo "✅ Container is running!"
    
    # Get the port from .env file or default to 8501
    PORT=$(grep APP_PORT .env 2>/dev/null | cut -d'=' -f2 || echo "8501")
    
    echo ""
    echo "🎉 Update completed successfully!"
    echo "📱 Application should be accessible at:"
    echo "   - Local: http://localhost:${PORT}"
    echo "   - Server: http://$(curl -s ifconfig.me):${PORT}"
    echo ""
    echo "📊 Container status:"
    docker-compose ps
    
else
    echo "❌ Container health check failed. Please check the logs:"
    echo "   docker-compose logs"
fi

echo ""
echo "🔍 To view real-time logs: docker-compose logs -f"
echo "🛑 To stop the application: docker-compose down"