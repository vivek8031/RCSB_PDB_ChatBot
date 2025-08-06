# 🧬 RCSB PDB ChatBot

An intelligent, multi-user research assistant for protein structures, crystallography, and structural biology data with complete conversation persistence.

## 🎯 Features

### ✅ **Multi-User Research Environment**
- **Individual research sessions** - Each researcher has their own workspace
- **Private conversation history** - Personal data storage for each user
- **Secure access control** - Research sessions are completely isolated
- **Professional deployment ready** - Tested and verified for research teams

### ✅ **Multi-Chat Management**
- **Multiple chats per user** - Organize conversations by topic
- **Chat persistence** - All messages saved and restored automatically
- **Chat switching** - Seamlessly switch between different conversations
- **Chat management** - Create, delete, and organize chats easily

### ✅ **Full Message Persistence**
- **Complete conversation history** - All messages saved with timestamps
- **Reference preservation** - Source documents and similarity scores stored
- **Cross-session continuity** - Messages persist across app restarts
- **Export functionality** - Download conversation history as text files

### ✅ **Modern UI/UX**
- **Clean authentication** - Simple user login/logout system
- **Intuitive interface** - Easy chat creation and navigation
- **Real-time streaming** - Live response display from RAGFlow
- **Settings panel** - Toggle references, clear chats, export data

## 🚀 Quick Start

### Local Development

#### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 2. Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your RAGFlow configuration
RAGFLOW_API_KEY=your_api_key_here
RAGFLOW_BASE_URL=http://127.0.0.1:9380
RAGFLOW_ASSISTANT_NAME=RCSB ChatBot v2
DEBUG_MODE=true
```

#### 3. Run the Application
```bash
streamlit run rcsb_pdb_chatbot.py
```

### Production Deployment

**🎯 Recommended: Git-Based Deployment**

For simple and efficient production deployment using Git:
- **[GIT-DEPLOYMENT.md](GIT-DEPLOYMENT.md)** - **⭐ New Git-based deployment guide**
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Legacy zip-based deployment guide

#### Quick Production Setup (Git-Based)
```bash
# Initial deployment (one-time setup)
./deploy-git.sh

# Future updates (after making changes)
git push origin main
./update-production.sh
```

#### Alternative: Manual Docker Setup
```bash
# Build and deploy with Docker Compose
docker-compose build
docker-compose up -d

# Access application
curl http://localhost:3002/_stcore/health
```

### 🖥️ Using the Interface
1. **Start a research session** with your research ID (e.g., "alice", "lab_researcher_123")
2. **Create a new chat** with a descriptive title for your research topic
3. **Ask questions** about RCSB PDB, protein structures, crystallography, etc.
4. **Organize research topics** in separate chats for better organization
5. **All conversations are automatically saved** for future reference

## 📁 Project Structure

```
📦 RCSB_PDB_ChatBot/
├── 🧬 rcsb_pdb_chatbot.py           # Main Streamlit research application
├── 🔧 user_session_manager.py       # User & session management system  
├── 🤖 ragflow_simple_client.py      # RAGFlow SDK wrapper
├── 📋 requirements.txt              # Python dependencies
├── 🐳 Dockerfile                    # Production container configuration
├── 🐳 docker-compose.yml           # Container orchestration
├── 🚀 deploy-git.sh                # Git-based deployment script (recommended)
├── 🔄 update-production.sh         # Quick production update script
├── 🚀 deploy.sh                    # Legacy deployment script
├── ⚙️ .env                         # Environment variables (production)
├── ⚙️ .env.example                 # Environment configuration template
├── 📊 user_data/                    # Research session data storage
│   ├── user_alice_sessions.json
│   ├── user_researcher_sessions.json
│   └── user_[research_id]_sessions.json
├── 📚 README.md                     # Project overview
├── 📖 GIT-DEPLOYMENT.md             # ⭐ Git-based deployment guide (recommended)
├── 📖 DEPLOYMENT.md                 # Legacy zip-based deployment guide
└── 🔧 TROUBLESHOOTING.md           # Common issues and solutions
```

## 🔬 Research Session Architecture

### **Multi-Researcher Model:**
```
Researcher "alice"              Researcher "bob"
├── 💬 Chat: "Protein Research"  ├── 💬 Chat: "NMR Studies"
├── 💬 Chat: "Data Analysis"     └── 💬 Chat: "Crystallography"
└── 💬 Chat: "PDB Questions"     
     ↓                               ↓
Research Sessions:              Research Sessions:
├── alice_Protein_Research_...  ├── bob_NMR_Studies_...
├── alice_Data_Analysis_...     └── bob_Crystallography_...
└── alice_PDB_Questions_...
```

### **Research Data Organization:**
- **Individual JSON files** per researcher in `user_data/` directory
- **Unique research sessions** prefixed with researcher ID
- **Private workspace** for each researcher
- **Automatic session validation** for data integrity

## 🛠️ Technical Details

### **Core Components:**

#### **1. User Session Manager (`user_session_manager.py`)**
- Manages user authentication and session creation
- Handles message storage and retrieval
- Provides chat lifecycle management (create, delete, clear)
- Ensures data isolation between users

#### **2. Research Interface (`rcsb_pdb_chatbot.py`)**
- Professional Streamlit-based web interface
- Research session management with start/end functionality
- Multi-chat interface with complete message persistence
- Research tools including export and reference controls

#### **3. RAGFlow Client (`ragflow_simple_client.py`)**
- Simplified wrapper around RAGFlow SDK
- Handles streaming responses and error management
- Provides clean API for the UI layer

### **Data Structure:**
```json
{
  "user_id": "alice",
  "session_name": "alice_main_session",
  "created_at": "2025-07-29T00:00:00",
  "chats": [
    {
      "chat_id": "uuid-123",
      "title": "Protein Research",
      "ragflow_session_id": "alice_Protein_Research_1722123456",
      "messages": [
        {
          "role": "user",
          "content": "What is RCSB PDB?",
          "timestamp": "2025-07-29T00:01:00",
          "references": null
        },
        {
          "role": "assistant", 
          "content": "The RCSB PDB is...",
          "timestamp": "2025-07-29T00:01:05",
          "references": [...]
        }
      ]
    }
  ]
}
```

## 🎯 Usage Examples

### **Basic Workflow:**
1. **Login:** `alice` logs in
2. **Create Chat:** "Protein Structure Analysis"
3. **Send Messages:** Ask about PDB structures
4. **Create Another Chat:** "Data Export Questions"
5. **Switch Between Chats:** All messages preserved
6. **Logout/Login:** Everything restored perfectly

### **Multi-User Scenario:**
- **Alice** works on protein research questions
- **Bob** analyzes crystallography data  
- **Charlie** studies NMR structures
- **All users isolated** - no cross-access or data mixing

### **Admin Features:**
- View total user count
- Clean up test data
- Monitor system usage

## 🚨 Security Features Verified

✅ **Session Isolation Test:** Users cannot see each other's sessions  
✅ **Chat History Protection:** Users cannot access other users' messages  
✅ **Data Persistence Security:** No cross-user data in storage files  
✅ **Session Hijacking Prevention:** Ownership validation before access  

## 🤖 RAGFlow Integration

- **Assistant:** 'RCSB ChatBot v2' (ID: 2af34abc5cf511f09eb5527b24292da5)
- **Dataset:** kb1 (RCSB PDB knowledge base)
- **API Key:** Configured for local RAGFlow instance
- **Base URL:** http://127.0.0.1:9380

## 📋 System Requirements

### Development Environment
- **Python:** 3.10+
- **Streamlit:** 1.28.0+
- **RAGFlow SDK:** 0.19.0+
- **RAGFlow Server:** Running on port 9380

### Production Environment
- **Docker:** 20.10+
- **Docker Compose:** 2.0+
- **Ubuntu:** 20.04+ (recommended)
- **Memory:** 2GB+ available
- **Storage:** 5GB+ free space
- **Ports:** 3002 available for application

## 🎉 What's New

### **✅ Production-Ready Deployment**
- **Git-based deployment**: Simple push-to-deploy workflow
- **Legacy zip deployment**: Complete Docker containerization
- **HAProxy integration**: Support on port 3002
- **Automated scripts**: One-command deployment and updates
- **Health checks**: Built-in monitoring and verification

### **✅ Enhanced Markdown Processing**
- Streamlined markdown rendering using Streamlit's built-in capabilities
- Support for ```markdown code block processing
- Clean UI without external dependencies
- Optimized for assistant-generated structured responses

### **✅ Secure Multi-User Architecture**
- Complete user isolation with individual data storage
- No session sharing or cross-user access possible
- Verified security through comprehensive testing

### **✅ Full Message Persistence** 
- All conversations automatically saved with timestamps
- Messages preserved across app restarts and user sessions
- Complete chat history restoration when switching between chats

### **✅ Professional UI/UX**
- Clean user authentication system
- Intuitive multi-chat interface
- Real-time message streaming with reference display
- Export and management tools

## 🔧 Configuration

The system is pre-configured for the RCSB PDB environment:
- **API Key:** `ragflow-VjNjM4Zjk0NmMyZDExZjA4MjQyNTY3YT`
- **Assistant:** 'RCSB ChatBot v2'
- **Knowledge Base:** RCSB PDB documentation and data

## 🎯 Perfect For

- **Research Teams** - Multiple researchers with isolated workspaces
- **Educational Use** - Students with separate conversation histories  
- **Multi-Project Work** - Organize different research topics in separate chats
- **Long-term Studies** - Complete conversation persistence and history

---

## 📚 Documentation

- **[GIT-DEPLOYMENT.md](GIT-DEPLOYMENT.md)** - ⭐ **Recommended Git-based deployment guide**
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Legacy zip-based deployment guide
- **[README.md](README.md)** - This project overview

## 🔗 Quick Links

- **Repository:** [https://github.com/vivek8031/RCSB_PDB_ChatBot](https://github.com/vivek8031/RCSB_PDB_ChatBot) ⭐ **Now Public**
- **Production URL:** http://YOUR_SERVER_IP (via HAProxy)
- **Health Check:** http://YOUR_SERVER_IP:3002/_stcore/health

---

**🔐 Security Notice:** This system provides complete user isolation and is safe for multi-user deployment. Each user's conversations are private and cannot be accessed by others.

**🚀 Ready to Use:** 
- **Development:** `streamlit run rcsb_pdb_chatbot.py`
- **Production (Git-based):** `./deploy-git.sh` then `./update-production.sh` for updates
- **Production (Manual):** `docker-compose up -d`