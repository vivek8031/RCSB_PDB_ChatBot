# 🧬 RCSB PDB ChatBot

An intelligent, multi-user research assistant for protein structures and structural biology powered by RAGFlow.

## ✨ Features

- **Multi-User Support** - Isolated research sessions for multiple users
- **Conversation Persistence** - All chats saved with complete history
- **Multi-Chat Organization** - Organize research by topic in separate chats
- **RAGFlow Integration** - Advanced AI responses with document references
- **Docker Deployment** - Production-ready containerized setup

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- RAGFlow server running
- Docker (for production)
- OpenAI API key for knowledge base processing

## 🎯 Deployment Options

Choose the right approach for your needs:

### Option 1: **Automated Deployment** (Recommended)

**For NEW installations:**
```bash
# 1. Clone repository
git clone https://github.com/vivek8031/RCSB_PDB_ChatBot.git
cd RCSB_PDB_ChatBot

# 2. Configure environment  
cp .env.example .env
nano .env  # Add RAGFLOW_API_KEY, RAGFLOW_BASE_URL, OPENAI_API_KEY

# 3. Deploy everything automatically
./deploy.sh
```

**For EXISTING deployments (updates):**
```bash
# Single command - updates code, knowledge base, and assistant
./update-server.sh
```

### Option 2: **Manual Setup** (Development)

**For local development or manual control:**

#### 1. **Install dependencies**
```bash
pip install -r requirements.txt
```

#### 2. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration:
# - RAGFLOW_API_KEY: Your RAGFlow API key
# - RAGFLOW_BASE_URL: RAGFlow server URL (e.g., http://127.0.0.1:9380)
# - OPENAI_API_KEY: Required for document processing
# - RAGFLOW_ASSISTANT_NAME: Name for your chat assistant
```

#### 3. **Setup RAGFlow Knowledge Base & Assistant** (Required)

The application requires both a knowledge base and chat assistant in RAGFlow:

```bash
# Step 3a: Create and populate knowledge base with documents
python3 knowledge_base/initialize_dataset.py --sync

# Step 3b: Create chat assistant linked to knowledge base  
python3 src/ragflow_assistant_manager.py
```

#### 4. **Run the application**
```bash
streamlit run src/rcsb_pdb_chatbot.py
```

## 📋 Script Reference

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `./deploy.sh` | **Initial deployment** | First-time setup, includes Docker validation, RAGFlow setup |
| `./update-server.sh` | **Production updates** | Existing deployments, pulls code updates, syncs knowledge base |
| Manual commands | **Development** | Local development, debugging, manual control |

### What Each Script Does

#### `./deploy.sh` - Complete Initial Setup
```bash
1. ✅ Validates Docker & Docker Compose installation
2. ✅ Creates .env from template (if missing)  
3. ✅ Creates user data directory
4. ✅ Builds and starts Docker containers
5. ✅ Waits for application health check
6. ✅ Creates RAGFlow knowledge base with documents
7. ✅ Creates RAGFlow chat assistant
8. ✅ Provides access URLs and management commands
```

#### `./update-server.sh` - Production Updates
```bash
1. ✅ Pulls latest code from GitHub
2. ✅ Stops existing containers  
3. ✅ Rebuilds containers with latest changes
4. ✅ Starts updated containers
5. ✅ Waits for health check
6. ✅ Syncs RAGFlow knowledge base (detects changes)
7. ✅ Updates RAGFlow assistant configuration
8. ✅ Reports deployment status
```

Works on any server with Docker - local, AWS, DigitalOcean, anywhere!

## 🔧 RAGFlow Setup & Troubleshooting

### Knowledge Base Management

**Sync documents (detects changes automatically):**
```bash
python3 knowledge_base/initialize_dataset.py --sync
```

**Force recreate knowledge base:**
```bash
python3 knowledge_base/initialize_dataset.py --force
```

**Check processing status:**
- Script shows real-time progress: `Progress: X/Y completed, Z running, W failed`
- Failed documents are automatically retried on next sync
- Look for `RETRY: filename (failed processing)` messages

### Assistant Management

**Create/update assistant:**
```bash
python3 src/ragflow_assistant_manager.py
```

**Test assistant:**
- Script automatically tests with a sample message
- Check for `✅ All tests passed!` confirmation
- Assistant links to knowledge base automatically

### Common Issues

**1. Documents fail processing with "disk usage exceeded flood-stage watermark"**
```bash
# Free up disk space
docker system prune -f --volumes

# Restart RAGFlow containers (clears Elasticsearch read-only mode)
cd ragflow/docker
docker compose -f docker-compose.yml down
docker compose -f docker-compose.yml up -d

# Retry processing
python3 knowledge_base/initialize_dataset.py --sync
```

**2. "chunk_token_num" parameter error (RAGFlow version mismatch)**
- Update to latest RAGFlow v0.20.5+
- Enhanced script detects and retries failed documents automatically

**3. Assistant not found or connection issues**
```bash
# Check RAGFlow connection
curl http://127.0.0.1:9380/health

# Verify API key in .env file
grep RAGFLOW_API_KEY .env
```

**4. OpenAI API key missing**
```bash
# Required for document processing
echo "OPENAI_API_KEY=your-key-here" >> .env
```

### Script Integration

Both knowledge base and assistant setup are included in deployment scripts:

- **deploy.sh**: Full initial setup
- **update-server.sh**: Updates with knowledge base sync
- **Scripts are idempotent**: Safe to run multiple times

## 🏗️ Architecture

```
📦 Universal Structure
├── src/                     # Application source code
├── Dockerfile              # Universal container image
├── docker-compose.yml      # Portable deployment
├── .env                    # All configuration here
└── user_data/              # Session storage (persisted)
```

## 🔧 Configuration

**Environment Variables (.env file):**
```bash
# App Configuration
APP_PORT=8501                # Port to run on
APP_HOST=0.0.0.0            # Host binding

# RAGFlow Settings  
RAGFLOW_API_KEY=your-api-key-here
RAGFLOW_BASE_URL=http://127.0.0.1:9380
RAGFLOW_ASSISTANT_NAME=RCSB ChatBot v2

# Data Storage
USER_DATA_DIR=./user_data   # Session data location
```

## 📱 Usage

1. **Start Research Session**: Login with your research ID (e.g., "alice", "researcher_123")
2. **Create Chats**: Organize different research topics in separate conversations
3. **Ask Questions**: Query about RCSB PDB, protein structures, crystallography
4. **Manage Sessions**: Switch between chats, export conversations, clear history

## 🧪 Multi-User Model

```
Researcher "alice"              Researcher "bob"
├── Chat: "Protein Research"    ├── Chat: "NMR Studies"
├── Chat: "Data Analysis"       └── Chat: "Crystallography"
└── Chat: "PDB Questions"
```

- **Complete Isolation**: Users cannot access each other's data
- **Private Workspaces**: Individual session storage
- **Secure Authentication**: Session validation and ownership checks

## 🛠️ Development

### Local Development
```bash
# Run without Docker
pip install -r requirements.txt
streamlit run src/rcsb_pdb_chatbot.py

# Or with Docker
docker-compose up -d
```

### Key Technologies
- **Frontend**: Streamlit
- **Backend**: Python 3.10+
- **AI Engine**: RAGFlow
- **Deployment**: Docker + Docker Compose
- **Data Storage**: JSON files

## 🔒 Security

- ✅ Complete user session isolation
- ✅ No cross-user data access
- ✅ Private conversation storage
- ✅ Session hijacking prevention
- ✅ Production-ready security practices

## 📚 Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment guide
- [CLAUDE.md](CLAUDE.md) - Development setup for Claude Code
- [docs/tree.md](docs/tree.md) - Feature documentation structure

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes following existing patterns
4. Test with multiple users and chat scenarios
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 🔗 Links

- **Repository**: https://github.com/vivek8031/RCSB_PDB_ChatBot
- **Issues**: https://github.com/vivek8031/RCSB_PDB_ChatBot/issues
- **RAGFlow**: https://github.com/infiniflow/ragflow