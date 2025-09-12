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
    echo "🧠 Setting up RAGFlow Knowledge Base & Assistant..."
    
    # Check if OpenAI API key exists
    if grep -q "OPENAI_API_KEY=" .env && ! grep -q "your-openai-api-key-here" .env; then
        echo "📚 Syncing knowledge base with latest documents..."
        if python3 knowledge_base/initialize_dataset.py --sync; then
            echo "✅ Knowledge base sync completed"
            
            echo "🤖 Creating/updating RAGFlow assistant..."
            if python3 src/ragflow_assistant_manager.py; then
                echo "✅ Assistant setup completed"
            else
                echo "⚠️  Assistant setup failed - check RAGFlow connection"
            fi
        else
            echo "⚠️  Knowledge base sync failed - continuing with deployment"
        fi
    else
        echo "⚠️  OpenAI API key not configured - skipping knowledge base setup"
        echo "   Add OPENAI_API_KEY to .env file to enable document processing"
    fi
    
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