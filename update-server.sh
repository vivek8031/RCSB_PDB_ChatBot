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

# User data management function
manage_user_data() {
    echo ""
    echo "📂 User Data Management"
    echo "======================"

    # Check if user_data directory exists and has content
    if [[ -d "user_data" ]] && [[ -n "$(ls -A user_data 2>/dev/null)" ]]; then
        echo "📊 Current user data found:"
        echo "   Directory: $(pwd)/user_data"
        ls -la user_data/ | grep "\.json$" | wc -l | xargs echo "   Session files:"

        echo ""
        echo "🔧 How would you like to handle existing user data?"
        echo "   1) Keep existing data (recommended)"
        echo "   2) Backup and clear data"
        echo "   3) Export data and clear"
        echo ""
        read -p "Choose option (1-3, default: 1): " data_choice

        case "${data_choice:-1}" in
            1)
                echo "✅ Keeping existing user data"
                ;;
            2)
                backup_user_data
                clear_user_data
                ;;
            3)
                export_user_data
                clear_user_data
                ;;
            *)
                echo "✅ Invalid option, keeping existing data"
                ;;
        esac
    else
        echo "📂 No existing user data found - starting fresh"
    fi
}

# Backup user data function
backup_user_data() {
    local timestamp=$(date +"%Y-%m-%d_%H%M%S")
    local backup_dir="backups/user_data_${timestamp}"

    echo "💾 Creating backup..."
    mkdir -p "${backup_dir}"

    if [[ -d "user_data" ]] && [[ -n "$(ls -A user_data 2>/dev/null)" ]]; then
        cp -r user_data/* "${backup_dir}/" 2>/dev/null || true
        echo "✅ Backup created: ${backup_dir}"
        echo "   Files backed up: $(ls -1 "${backup_dir}" | wc -l)"
    else
        echo "⚠️  No data to backup"
    fi
}

# Export user data function
export_user_data() {
    local timestamp=$(date +"%Y-%m-%d_%H%M%S")
    local export_dir="exports/user_data_${timestamp}"

    echo "📤 Exporting user data..."
    mkdir -p "${export_dir}"

    if [[ -d "user_data" ]] && [[ -n "$(ls -A user_data 2>/dev/null)" ]]; then
        cp -r user_data/* "${export_dir}/" 2>/dev/null || true
        echo "✅ Data exported to: ${export_dir}"

        # Create a summary file
        echo "# User Data Export Summary" > "${export_dir}/export_summary.md"
        echo "Export Date: $(date)" >> "${export_dir}/export_summary.md"
        echo "Files Exported:" >> "${export_dir}/export_summary.md"
        ls -la "${export_dir}"/*.json 2>/dev/null | awk '{print "- " $9}' >> "${export_dir}/export_summary.md" || true
    else
        echo "⚠️  No data to export"
    fi
}

# Clear user data function
clear_user_data() {
    echo ""
    read -p "🗑️  Are you sure you want to clear all user data? (y/N): " confirm

    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        if [[ -d "user_data" ]]; then
            rm -rf user_data/*
            echo "✅ User data cleared"
        fi
        # Recreate directory structure
        mkdir -p user_data
        echo "📁 Empty user_data directory ready"
    else
        echo "❌ Clear operation cancelled"
    fi
}

# Manage user data before update
manage_user_data

echo ""
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