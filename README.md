# 🧬 RCSB PDB ChatBot

An intelligent help desk chatbot for protein structures and structural biology powered by RAGFlow.

## ✨ Features

- **Anonymous Sessions** - No login required, auto-generated session IDs
- **Conversation Persistence** - All chats saved with complete history
- **Star Ratings** - 1-5 star feedback on each response
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

### Google Drive Integration (Optional)

Automatically sync documents from Google Drive to the knowledge base.

**Initial Setup:**

1. **Get Google Cloud credentials:**
   ```bash
   # Follow guide: https://console.cloud.google.com/
   # 1. Create/select project
   # 2. Enable Google Drive API
   # 3. Create OAuth 2.0 Desktop credentials
   # 4. Download credentials JSON
   ```

2. **Configure credentials (K8s-friendly):**
   ```bash
   # Place credentials in project directory (works for local & K8s)
   cp ~/Downloads/client_secret_*.json credentials/google_drive_credentials.json

   # Credentials will be stored in: credentials/google_drive_token.pickle (auto-generated)
   ```

3. **Configure .env file:**
   ```bash
   # Add these lines to .env
   GOOGLE_DRIVE_FOLDER_URL=https://drive.google.com/drive/folders/YOUR_FOLDER_ID
   # Paths are project-relative (K8s-ready):
   GOOGLE_DRIVE_CREDENTIALS_PATH=credentials/google_drive_credentials.json
   GOOGLE_DRIVE_TOKEN_PATH=credentials/google_drive_token.pickle
   ```

4. **Run OAuth setup (one-time, local):**
   ```bash
   python scripts/setup_google_drive.py
   # Browser will open - sign in and grant permissions
   # Token saved to credentials/google_drive_token.pickle
   ```

**K8s Deployment:**
   ```yaml
   # Mount credentials as secrets
   apiVersion: v1
   kind: Secret
   metadata:
     name: google-drive-creds
   type: Opaque
   data:
     credentials.json: <base64-encoded-client-secret>
     token.pickle: <base64-encoded-token>

   # Mount in pod:
   volumeMounts:
     - name: google-creds
       mountPath: /app/credentials
       readOnly: true
   ```

**Usage:**

```bash
# Manual sync
python -m src.google_drive_sync.sync_manager

# Set up automatic hourly sync (cron)
crontab -e
# Add this line:
0 * * * * /path/to/chatbot_ui_v2/scripts/sync_google_drive.sh
```

**How it works:**

The sync system operates in two phases:

**Phase 1: Google Drive Download (Simple, Always Fresh)**
```
1. List all files in Google Drive folder
2. Filter out spreadsheets (only keep documents & PDFs)
3. Download every file:
   - Google Docs/Sheets/Slides → Export as PDF via Drive API
   - PDFs → Download directly
4. Save to knowledge_base/ folder (overwrites if exists)

Note: Downloads ALL files every time (no state tracking at Drive level)
```

**Phase 2: RAGFlow Sync (Smart, Change Detection)**
```
1. Read knowledge_base/ directory
2. Compare with existing RAGFlow dataset
3. Detect changes using file size comparison:
   - NEW: File not in RAGFlow → Upload
   - UPDATED: Size changed → Re-upload
   - DELETED: In RAGFlow but not local → Remove
   - UNCHANGED: Same size → Skip upload
4. Apply changes to RAGFlow knowledge base

State maintained: Only in RAGFlow database
```

**Where Checks Happen:**
| Phase | Location | What's Checked | State Maintained |
|-------|----------|----------------|------------------|
| Google Drive | Drive API | None (downloads all) | ❌ No state file |
| RAGFlow Sync | initialize_dataset.py | File size, processing status | ✅ RAGFlow DB |

**Why This Design:**
- **Simple**: No complex state tracking at Drive level
- **Reliable**: Always in sync (no stale state issues)
- **Efficient Upload**: RAGFlow only uploads changed files
- **Trade-off**: Re-downloads unchanged files (bandwidth cost for simplicity)

**Supported file types:**
- Google Docs/Sheets/Slides (exported as PDF)
- PDF files (downloaded directly)
- Spreadsheets are skipped automatically

### Feedback Export to Google Sheets (Optional)

Export user conversations, feedback, and ratings to Google Sheets for analysis.

**What Gets Exported:**
- User questions and AI responses (Q&A pairs)
- Star ratings (1-5 stars on each response)
- Referenced documents used by AI
- Timestamps for all interactions
- Organized by session and chat title

**Initial Setup:**

Uses the same OAuth credentials as Google Drive sync. If you've already set up Drive sync, just enable Sheets API:

1. **Enable Google Sheets API:**
   ```bash
   # Go to Google Cloud Console: https://console.cloud.google.com/
   # Navigate to: APIs & Services > Library
   # Search for "Google Sheets API"
   # Click "Enable"
   ```

2. **Re-authorize with Sheets scope:**
   ```bash
   # Remove old token
   rm -f credentials/google_drive_token.pickle

   # Re-run OAuth setup (grants both Drive and Sheets access)
   python scripts/setup_google_drive.py
   # Browser will open - sign in and grant permissions
   ```

3. **Configure .env file (optional):**
   ```bash
   # Add these lines to .env
   GOOGLE_SHEETS_EXPORT_SPREADSHEET_ID=  # Leave empty to create new spreadsheet
   GOOGLE_SHEETS_EXPORT_SPREADSHEET_NAME=RCSB_ChatBot_Feedback_Export
   GOOGLE_DRIVE_EXPORT_FOLDER_ID=  # Optional: folder to create spreadsheet in
   ```

**Usage:**

```bash
# Manual export
python scripts/export_feedback_to_drive.py

# Set up automatic daily export (cron)
crontab -e
# Add this line:
0 0 * * * /path/to/chatbot_ui_v2/scripts/export_feedback.sh
```

**Spreadsheet Structure:**

Each row represents one Q&A interaction:

| Column | Description |
|--------|-------------|
| Export ID | Unique identifier for this Q&A pair |
| User ID | Session ID (UUID) |
| Chat Title | Topic/title of the conversation |
| Question Timestamp | When the question was asked |
| User Question | The user's question text |
| Answer Timestamp | When AI responded |
| AI Response | The AI's answer text |
| Star Rating | 1-5 star rating (if provided) |
| Feedback Timestamp | When feedback was given |
| Referenced Documents | Which knowledge base documents AI used |

**How It Works:**

1. **Extraction:** Reads all `user_data/*.json` files
2. **Pairing:** Matches user questions with AI responses
3. **Deduplication:** Only appends new Q&A pairs (checks message IDs)
4. **Upload:** Appends to Google Sheet with formatting
5. **Result:** Clean, readable spreadsheet for non-technical users

**Features:**

- **Append-only:** New data added without deleting existing rows
- **No duplicates:** Tracks exported message IDs to avoid re-exporting
- **Formatted:** Frozen header row, wrapped text, auto-filter enabled
- **Collaborative:** Multiple people can view/analyze the spreadsheet
- **Manual edits preserved:** Your spreadsheet changes won't be overwritten

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

1. **Open the App**: Session is created automatically (no login required)
2. **Ask Questions**: Query about RCSB PDB, protein structures, crystallography
3. **Rate Responses**: Click stars (1-5) to rate each AI response
4. **New Chat**: Click "New Chat" button to start a fresh conversation

## 🧪 Session Model

```
Anonymous Session (UUID-based)
├── Auto-generated session ID in URL (?sid=...)
├── Chat: "Help Session 2026-01-14 10:30"
└── All data persisted for admin review
```

- **No Login Required**: Sessions auto-created on first visit
- **Session Isolation**: Each browser gets unique session ID
- **Data Persistence**: All chats saved for admin purposes

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

- ✅ Session-based data isolation (UUID per browser)
- ✅ All conversations persisted securely
- ✅ No authentication required (anonymous help desk)
- ✅ Data accessible to admins for quality review
- ✅ Production-ready containerized deployment

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