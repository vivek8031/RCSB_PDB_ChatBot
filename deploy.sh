#!/bin/bash

# RCSB PDB ChatBot - Simple Universal Deployment
# Works on any server with Docker and Docker Compose

set -e

echo "🚀 RCSB PDB ChatBot - Universal Deployment"
echo "========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null && ! docker-compose --version &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose:"
    echo "   https://docs.docker.com/compose/install/"
    exit 1
fi

# Check if .env file exists
if [[ ! -f .env ]]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "✅ Created .env file from template"
    echo ""
    echo "🔧 IMPORTANT: Edit .env file with your configuration:"
    echo "   - Set RAGFLOW_API_KEY to your actual API key"
    echo "   - Update RAGFLOW_BASE_URL if needed"
    echo "   - Adjust APP_PORT if required (default: 8501)"
    echo ""
    echo "Then run this script again to deploy."
    exit 0
fi

# Load environment variables
source .env

# Create user data directory if it doesn't exist
USER_DATA_DIR=${USER_DATA_DIR:-./user_data}
mkdir -p "$USER_DATA_DIR"
echo "✅ User data directory ready: $USER_DATA_DIR"

# Use docker compose (v2) if available, fallback to docker-compose (v1)
DOCKER_COMPOSE_CMD="docker compose"
if ! docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
fi

# Deploy the application
echo "🐳 Building and starting containers..."
$DOCKER_COMPOSE_CMD up -d --build

# Wait for health check
echo "⏳ Waiting for application to be ready..."
sleep 15

# Check if the application is running
APP_PORT=${APP_PORT:-8501}
if curl -f -s "http://localhost:$APP_PORT/_stcore/health" > /dev/null 2>&1; then
    echo "✅ Application is running successfully!"
    
    echo ""
    echo "🧠 Setting up RAGFlow Knowledge Base & Assistant..."
    
    # Check if OpenAI API key exists and is configured
    if grep -q "OPENAI_API_KEY=" .env && ! grep -q "your-openai-api-key-here" .env; then
        echo "📚 Creating knowledge base with documents..."
        if python3 knowledge_base/initialize_dataset.py --sync; then
            echo "✅ Knowledge base setup completed"
            
            echo "🤖 Creating RAGFlow assistant..."
            if python3 src/ragflow_assistant_manager.py; then
                echo "✅ Assistant setup completed"
            else
                echo "⚠️  Assistant setup failed - check RAGFlow connection"
                echo "   You can run manually: python3 src/ragflow_assistant_manager.py"
            fi
        else
            echo "⚠️  Knowledge base setup failed - check configuration"
            echo "   You can run manually: python3 knowledge_base/initialize_dataset.py --sync"
        fi
    else
        echo "⚠️  OpenAI API key not configured - skipping RAGFlow setup"
        echo ""
        echo "🔧 To enable full RAGFlow integration:"
        echo "   1. Add OPENAI_API_KEY to .env file"
        echo "   2. Run: python3 knowledge_base/initialize_dataset.py --sync"
        echo "   3. Run: python3 src/ragflow_assistant_manager.py"
    fi
    
    echo ""
    echo "🌐 Access your RCSB PDB ChatBot at:"
    echo "   http://localhost:$APP_PORT"
    echo ""
    echo "📋 Management commands:"
    echo "   - View logs: $DOCKER_COMPOSE_CMD logs -f"
    echo "   - Restart: $DOCKER_COMPOSE_CMD restart"  
    echo "   - Stop: $DOCKER_COMPOSE_CMD down"
    echo "   - Update: ./update-server.sh"
else
    echo "⚠️  Application may not be ready yet. Check logs:"
    echo "   $DOCKER_COMPOSE_CMD logs"
    echo ""
    echo "🌐 Try accessing: http://localhost:$APP_PORT"
fi

echo ""
echo "🎉 Deployment complete!"