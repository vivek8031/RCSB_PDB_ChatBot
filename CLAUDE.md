# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a multi-user research chatbot for RCSB PDB (Protein Data Bank) built with Streamlit and RAGFlow. The application provides isolated research environments for multiple users with complete conversation persistence and chat management.

## Architecture

### Core Components

**Main Application** (`rcsb_pdb_chatbot.py`)
- Streamlit-based web interface
- Multi-user authentication and session management
- Chat creation, switching, and management
- Real-time streaming responses from RAGFlow
- Message persistence and export functionality

**User Session Manager** (`user_session_manager.py`) 
- Handles user authentication and session isolation
- Manages multiple chats per user with unique RAGFlow session IDs
- Provides message storage/retrieval with JSON persistence
- Ensures complete data isolation between users

**RAGFlow Client** (`ragflow_simple_client.py`)
- Simplified wrapper around RAGFlow SDK
- Manages streaming responses and API communication
- Handles error management and connection to RAGFlow assistant
- Provides clean API interface for the UI layer

### Data Storage Architecture

- User data stored in `user_data/` directory as individual JSON files
- Each user gets a file: `user_[research_id]_sessions.json`
- Complete message history with timestamps and RAGFlow references
- Chat isolation with unique RAGFlow session IDs per chat

## Development Commands

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run rcsb_pdb_chatbot.py

# Test with specific user
# Navigate to app and login with research ID (e.g., "alice", "researcher_123")
```

### Production Deployment

**Recommended: Git-Based Deployment**
```bash
# Initial deployment (one-time setup)
./deploy-git.sh

# Update production after changes
git push origin main
./update-production.sh
```

**Alternative: Docker Deployment**
```bash
# Build and run with Docker Compose
docker-compose build
docker-compose up -d

# Check health
curl http://localhost:3002/_stcore/health

# View logs
docker-compose logs -f rcsb-pdb-chatbot
```

### Testing
```bash
# Test RAGFlow connection
python ragflow_simple_client.py

# Test session management
python user_session_manager.py

# Manual UI testing workflow:
# 1. Login with test user ID
# 2. Create multiple chats
# 3. Send messages and verify persistence
# 4. Test chat switching and deletion
# 5. Verify user isolation (login as different user)
```

## Configuration

### Environment Variables (.env)
```bash
RAGFLOW_API_KEY=your_api_key_here
RAGFLOW_BASE_URL=http://127.0.0.1:9380
RAGFLOW_ASSISTANT_NAME=RCSB ChatBot v2
DEBUG_MODE=true
```

### RAGFlow Integration
- **Assistant:** 'RCSB ChatBot v2' (ID: 2af34abc5cf511f09eb5527b24292da5)
- **Dataset:** kb1 (RCSB PDB knowledge base) 
- **Local RAGFlow:** Must be running on port 9380

## Key Design Patterns

### User Session Management
- Each user identified by research ID (e.g., "alice", "lab_researcher_123")
- RAGFlow session IDs formatted as: `{user_id}_{chat_title}_{timestamp}`
- Complete data isolation - users cannot access other users' data
- Automatic session validation and cleanup

### Message Persistence
- All messages stored with timestamps and RAGFlow references
- Messages preserved across app restarts and user sessions
- Chat history restored when switching between chats
- Export functionality for conversation download

### Multi-Chat Architecture
- Users can create multiple chats for different research topics
- Each chat has unique RAGFlow session for context isolation
- Chat titles and message counts tracked for organization
- Seamless switching between chats with full message history

## Common Development Tasks

### Adding New Features
1. Check existing patterns in the three core files
2. Maintain user isolation principles
3. Update session data structure if needed
4. Test with multiple users and chats
5. Verify data persistence across restarts

### Debugging Multi-User Issues
1. Check `user_data/` directory for session files
2. Verify RAGFlow session ID generation in `user_session_manager.py:130`
3. Test with different user IDs to ensure isolation
4. Check Streamlit session state management

### Production Deployment Issues
1. Use health check: `curl http://localhost:3002/_stcore/health`
2. Check Docker logs: `docker-compose logs -f rcsb-pdb-chatbot`
3. Verify .env configuration matches production RAGFlow instance
4. Ensure `user_data/` directory permissions are correct

## Security Considerations

- Complete user isolation verified through testing
- No cross-user data access possible
- Session hijacking prevention with ownership validation
- Private workspace for each researcher
- No sensitive data in code or version control