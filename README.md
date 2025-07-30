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

### 1. Install Dependencies
```bash
pip install streamlit ragflow-sdk
```

### 2. Run the Application
```bash
streamlit run rcsb_pdb_chatbot.py
```

### 3. Use the Interface
1. **Start a research session** with your research ID (e.g., "alice", "lab_researcher_123")
2. **Create a new chat** with a descriptive title for your research topic
3. **Ask questions** about RCSB PDB, protein structures, crystallography, etc.
4. **Organize research topics** in separate chats for better organization
5. **All conversations are automatically saved** for future reference

## 📁 Project Structure

```
📦 chatbot_ui_v2/
├── 🧬 rcsb_pdb_chatbot.py           # Main Streamlit research application
├── 🔧 user_session_manager.py       # User & session management system
├── 🤖 ragflow_simple_client.py      # RAGFlow SDK wrapper
├── 📊 user_data/                    # Research session data storage
│   ├── user_alice_sessions.json
│   ├── user_researcher_sessions.json
│   └── user_[research_id]_sessions.json
└── 📚 README.md                     # This documentation
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

- **Python:** 3.8+
- **Streamlit:** 1.28.0+
- **RAGFlow SDK:** 0.19.0+
- **RAGFlow Server:** Running locally on port 9380

## 🎉 What's New

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

**🔐 Security Notice:** This system provides complete user isolation and is safe for multi-user deployment. Each user's conversations are private and cannot be accessed by others.

**🚀 Ready to Use:** Simply run `streamlit run rcsb_pdb_chatbot.py` and start researching!