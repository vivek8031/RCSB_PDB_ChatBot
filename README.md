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

### Local Development

1. **Install dependencies**
```bash
pip install -r requirements.txt
```

2. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your RAGFlow configuration
```

3. **Run the application**
```bash
streamlit run rcsb_pdb_chatbot.py
```

### Universal Deployment (Any Server)

```bash
# Clone the repository
git clone https://github.com/vivek8031/RCSB_PDB_ChatBot.git
cd RCSB_PDB_ChatBot

# Configure environment
cp .env.example .env
nano .env  # Add your RAGFlow API key and settings

# Deploy with one command
./deploy.sh
```

Works on any server with Docker - local, AWS, DigitalOcean, anywhere!

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