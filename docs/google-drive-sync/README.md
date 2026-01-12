# Google Drive Sync Feature Documentation

This document provides detailed instructions on how the Google Drive sync feature works, what each script does, and how to set it up.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Configuration](#configuration)
5. [Step-by-Step Workflow](#step-by-step-workflow)
6. [Script Details](#script-details)
7. [Running the Sync](#running-the-sync)
8. [Logs and Monitoring](#logs-and-monitoring)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The Google Drive sync feature automatically synchronizes documents from a Google Drive folder to the RAGFlow chatbot's knowledge base. This enables the chatbot to answer questions based on the latest documents without manual intervention.

### What It Does

1. **Downloads** documents from a configured Google Drive folder
2. **Converts** various formats (Google Docs, webpages) to PDF
3. **Syncs** documents to RAGFlow knowledge base with intelligent change detection
4. **Processes** documents with AI-powered chunking and embeddings

### Supported Document Types

| Source Type | Processing |
|-------------|------------|
| PDF files | Downloaded directly |
| Google Docs | Exported to PDF |
| Google Sheets | Exported to PDF |
| Google Slides | Exported to PDF |
| Webpages (URLs) | Converted to PDF using Playwright |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GOOGLE DRIVE SYNC PIPELINE                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│   Google Drive       │
│   Shared Folder      │
│   ┌────────────────┐ │
│   │ Document 1.pdf │ │
│   │ Report.docx    │ │
│   │ Data.xlsx      │ │
│   └────────────────┘ │
└──────────┬───────────┘
           │
           │ OAuth 2.0 Authentication
           │ Google Drive API
           ▼
┌──────────────────────┐
│  STAGE 1: Download   │
│  sync_manager.py     │
│  drive_client.py     │
│                      │
│  - List folder files │
│  - Export to PDF     │
│  - Download files    │
└──────────┬───────────┘
           │
           │ Files saved to knowledge_base/
           ▼
┌──────────────────────┐
│  Local Storage       │
│  knowledge_base/     │
│  ┌────────────────┐  │
│  │ Document1.pdf  │  │
│  │ Report.pdf     │  │
│  │ Data.pdf       │  │
│  └────────────────┘  │
└──────────┬───────────┘
           │
           │ subprocess.run()
           ▼
┌──────────────────────┐
│  STAGE 2: RAGFlow    │
│  initialize_dataset  │
│                      │
│  - Detect changes    │
│  - Upload new docs   │
│  - Delete removed    │
│  - Trigger parsing   │
└──────────┬───────────┘
           │
           │ RAGFlow SDK API
           ▼
┌──────────────────────┐
│  RAGFlow Server      │
│  Knowledge Base      │
│                      │
│  - DeepDoc parsing   │
│  - Text chunking     │
│  - RAPTOR summary    │
│  - Vector embeddings │
└──────────────────────┘
           │
           ▼
┌──────────────────────┐
│  Chatbot Ready!      │
│  Documents indexed   │
│  and searchable      │
└──────────────────────┘
```

---

## Prerequisites

### 1. Google Cloud Project Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the **Google Drive API**
4. Create OAuth 2.0 credentials:
   - Go to APIs & Services → Credentials
   - Create OAuth 2.0 Client ID
   - Application type: Desktop App
   - Download the credentials JSON file

### 2. Required Python Packages

```bash
pip install google-auth google-auth-oauthlib google-api-python-client
pip install playwright  # For webpage to PDF conversion
playwright install chromium  # Install browser for Playwright
```

### 3. RAGFlow Server

Ensure RAGFlow is running and accessible:

```bash
# Check RAGFlow health
curl http://127.0.0.1:9380/api/v1/health
```

---

## Configuration

### Environment Variables (.env)

Create or update your `.env` file with the following:

```bash
# Google Drive Configuration
GOOGLE_DRIVE_FOLDER_URL=https://drive.google.com/drive/folders/YOUR_FOLDER_ID
GOOGLE_DRIVE_CREDENTIALS_PATH=credentials/google_drive_credentials.json
GOOGLE_DRIVE_TOKEN_PATH=credentials/google_drive_token.pickle

# RAGFlow Configuration
RAGFLOW_API_KEY=your_ragflow_api_key
RAGFLOW_BASE_URL=http://127.0.0.1:9380

# OpenAI (for embeddings)
OPENAI_API_KEY=your_openai_api_key
```

### Credentials Setup

1. Place your Google OAuth credentials file at:
   ```
   credentials/google_drive_credentials.json
   ```

2. Run the setup script to generate OAuth token:
   ```bash
   python scripts/setup_google_drive.py
   ```
   This will open a browser for authentication and create `google_drive_token.pickle`.

---

## Step-by-Step Workflow

### Step 1: Authentication

```
sync_manager.py initializes
        │
        ▼
drive_client.py loads OAuth token from pickle file
        │
        ▼
If token expired → Refresh using refresh_token
        │
        ▼
Google Drive API service initialized
```

### Step 2: Folder Discovery

```
Extract folder ID from GOOGLE_DRIVE_FOLDER_URL
        │
        ▼
Verify folder access permissions
        │
        ▼
List all files in folder using Drive API
        │
        ▼
Filter: Exclude spreadsheets used for configuration
```

### Step 3: File Download

```
For each file in folder:
        │
        ├─► If Google Doc/Sheet/Slides:
        │       Export as PDF using Drive API
        │       Save to knowledge_base/filename.pdf
        │
        ├─► If PDF file:
        │       Download directly
        │       Save to knowledge_base/filename.pdf
        │
        └─► If Webpage URL (from spreadsheet):
                Use Playwright to render page
                Convert to PDF
                Save to knowledge_base/filename.pdf
```

### Step 4: Trigger RAGFlow Sync

```
sync_manager.py spawns subprocess:
python knowledge_base/initialize_dataset.py --sync
        │
        ▼
initialize_dataset.py starts
```

### Step 5: Change Detection

```
Scan knowledge_base/ directory
        │
        ▼
Get list of existing documents from RAGFlow
        │
        ▼
Compare by filename and file size:
        │
        ├─► NEW: File exists locally but not in RAGFlow
        │       → Mark for upload
        │
        ├─► UPDATED: File size changed
        │       → Delete old, upload new
        │
        ├─► DELETED: File in RAGFlow but not locally
        │       → Mark for deletion
        │
        └─► UNCHANGED: Same filename and size
                → Skip processing
```

### Step 6: Apply Changes to RAGFlow

```
Delete removed documents from RAGFlow dataset
        │
        ▼
Upload new and updated documents
        │
        ▼
Trigger async document parsing
        │
        ▼
Monitor processing progress until complete
```

### Step 7: Document Processing (Inside RAGFlow)

```
For each uploaded document:
        │
        ├─► DeepDoc PDF Parsing
        │       Extracts text preserving layout
        │       Handles tables, images, columns
        │
        ├─► Naive Chunking
        │       Splits into 512-token chunks
        │       Uses newline as delimiter
        │
        ├─► RAPTOR Hierarchical Summarization
        │       Creates multi-level summaries
        │       Enables abstract question answering
        │
        └─► Vector Embeddings
                Uses OpenAI text-embedding-3-large
                Stores in vector database
```

---

## Script Details

### `src/google_drive_sync/sync_manager.py`

**Purpose:** Main orchestrator for the entire sync process

**Key Functions:**

| Function | Description |
|----------|-------------|
| `sync()` | Main entry point - downloads files and triggers RAGFlow sync |
| `trigger_ragflow_sync()` | Spawns subprocess to run initialize_dataset.py |

**What It Does:**
1. Initializes Google Drive client
2. Lists files in configured folder
3. Downloads/exports each file to PDF
4. Calls initialize_dataset.py to sync with RAGFlow
5. Reports success/failure statistics

---

### `src/google_drive_sync/drive_client.py`

**Purpose:** Google Drive API wrapper

**Key Functions:**

| Function | Description |
|----------|-------------|
| `_authenticate()` | Loads/refreshes OAuth token |
| `list_folder_files(folder_id)` | Lists all files in a folder |
| `download_file(file_id, path)` | Downloads binary files (PDFs) |
| `export_to_pdf(file_id, path)` | Exports Google Docs to PDF |
| `get_file_metadata(file_id)` | Gets file info (name, size, type) |

**Authentication Flow:**
```python
1. Load token from pickle file
2. Check if token is expired
3. If expired, use refresh_token to get new access_token
4. Save updated token to pickle file
5. Build Google Drive API service
```

---

### `src/google_drive_sync/config.py`

**Purpose:** Configuration management

**Key Classes:**

| Class | Description |
|-------|-------------|
| `SyncConfig` | Loads configuration from environment variables |
| `SyncResults` | Dataclass for sync operation results |

**Configuration Loaded:**
- Google Drive folder URL
- Credentials file path
- Token file path
- Output directory (knowledge_base/)

---

### `knowledge_base/initialize_dataset.py`

**Purpose:** RAGFlow knowledge base sync with intelligent change detection

**Key Functions:**

| Function | Description |
|----------|-------------|
| `sync_knowledge_base()` | Main sync orchestrator |
| `get_local_files_with_metadata()` | Scans local files with size/mtime |
| `get_existing_documents_map()` | Gets documents from RAGFlow |
| `detect_file_changes()` | Compares local vs RAGFlow documents |
| `apply_document_changes()` | Uploads/deletes documents |
| `process_changed_documents()` | Triggers RAGFlow parsing |
| `monitor_processing_progress()` | Waits for parsing to complete |

**Change Detection Algorithm:**
```python
for each local_file:
    if not in ragflow:
        mark as NEW
    elif size != ragflow_size:
        mark as UPDATED
    elif processing failed:
        mark for RETRY

for each ragflow_doc:
    if not in local_files:
        mark as DELETED
```

---

### `scripts/sync_google_drive.sh`

**Purpose:** Shell wrapper for automated/cron execution

**What It Does:**
1. Activates Python virtual environment
2. Sets up environment variables
3. Runs sync_manager.py
4. Captures and logs output
5. Reports success/failure

**Cron Job Example:**
```bash
# Run every hour
0 * * * * /path/to/chatbot_ui_v2/scripts/sync_google_drive.sh
```

---

## Running the Sync

### Manual Sync

```bash
# Full sync (Google Drive + RAGFlow)
python -m src.google_drive_sync.sync_manager

# RAGFlow only (sync local files)
python knowledge_base/initialize_dataset.py --sync

# RAGFlow with verbose logging
python knowledge_base/initialize_dataset.py --sync --verbose

# Force recreate dataset (deletes existing)
python knowledge_base/initialize_dataset.py --force
```

### Using Shell Script

```bash
# Make executable
chmod +x scripts/sync_google_drive.sh

# Run
./scripts/sync_google_drive.sh
```

### Automated (Cron)

```bash
# Edit crontab
crontab -e

# Add hourly sync
0 * * * * /path/to/scripts/sync_google_drive.sh >> /path/to/logs/cron.log 2>&1
```

---

## Logs and Monitoring

### Log Location

```
logs/google_drive_sync.log
```

### Log Format

```
2025-11-13 00:22:40 - google_drive_sync - INFO - Starting Google Drive Sync
2025-11-13 00:22:40 - google_drive_sync.drive_client - INFO - Loaded existing OAuth token
2025-11-13 00:22:41 - google_drive_sync - INFO - Found 5 files to download
2025-11-13 00:22:43 - google_drive_sync - INFO - ✓ Downloaded: Document.pdf
2025-11-13 00:22:49 - google_drive_sync - INFO - ✓ RAGFlow sync completed successfully
```

### Monitoring Commands

```bash
# Watch logs in real-time
tail -f logs/google_drive_sync.log

# Check last sync status
tail -50 logs/google_drive_sync.log | grep "Sync Report" -A 20

# Count successful syncs today
grep "$(date +%Y-%m-%d)" logs/google_drive_sync.log | grep "Success" | wc -l
```

### Sync Report Example

```
============================================================
Google Drive Sync Report
============================================================
Start Time: 2025-11-13T00:22:40.211678
End Time: 2025-11-13T00:22:49.596366
Duration: 9.4 seconds

Results:
  Total Links: 5
  Successful: 5
  Failed: 0
  Success Rate: 100.0%

RAGFlow Sync: ✓ Success

Downloaded Files:
  - Document1.pdf
  - Document2.pdf
  - Report.pdf

Errors:
  None
============================================================
```

---

## Troubleshooting

### Common Issues

#### 1. OAuth Token Expired

**Symptom:** `RefreshError: The credentials do not contain the necessary refresh token`

**Solution:**
```bash
# Delete old token and re-authenticate
rm credentials/google_drive_token.pickle
python scripts/setup_google_drive.py
```

#### 2. Folder Not Found

**Symptom:** `HttpError 404: File not found`

**Solution:**
- Verify folder URL in `.env` is correct
- Ensure the folder is shared with your Google account
- Check folder ID extraction from URL

#### 3. RAGFlow Connection Failed

**Symptom:** `ConnectionError: Cannot connect to RAGFlow`

**Solution:**
```bash
# Check RAGFlow is running
curl http://127.0.0.1:9380/api/v1/health

# Verify API key
echo $RAGFLOW_API_KEY
```

#### 4. IndexError: list index out of range

**Symptom:** Sync fails with `IndexError('list index out of range')`

**Solution:** This was fixed by adding defensive checks. Update to the latest code:
```bash
git pull origin main
```

#### 5. Document Processing Timeout

**Symptom:** `Processing timeout reached`

**Solution:**
- Large documents may take longer to process
- Increase timeout in `monitor_processing_progress()` if needed
- Check RAGFlow server resources (CPU/memory)

### Debug Mode

Run with verbose logging:
```bash
python knowledge_base/initialize_dataset.py --sync --verbose
```

### Health Check

```bash
# Check all components
python -c "
from src.ragflow_assistant_manager import create_assistant_manager
manager = create_assistant_manager()
print(manager.health_check())
"
```

---

## File Structure

```
chatbot_ui_v2/
├── src/
│   └── google_drive_sync/
│       ├── __init__.py
│       ├── sync_manager.py      # Main orchestrator
│       ├── drive_client.py      # Google Drive API wrapper
│       └── config.py            # Configuration classes
├── knowledge_base/
│   ├── initialize_dataset.py    # RAGFlow sync script
│   ├── *.pdf                    # Downloaded documents
│   └── README.md
├── credentials/
│   ├── google_drive_credentials.json  # OAuth client ID
│   └── google_drive_token.pickle      # OAuth access token
├── scripts/
│   ├── sync_google_drive.sh     # Shell wrapper
│   └── setup_google_drive.py    # OAuth setup script
├── logs/
│   └── google_drive_sync.log    # Sync logs
└── .env                         # Environment variables
```

---

## Summary

The Google Drive sync feature provides an automated pipeline to keep your chatbot's knowledge base up-to-date with documents from Google Drive. It handles:

- **Authentication:** OAuth 2.0 with automatic token refresh
- **Download:** Multiple file types exported/converted to PDF
- **Change Detection:** Only processes new/updated documents
- **Processing:** AI-powered parsing, chunking, and embeddings
- **Monitoring:** Detailed logging and progress tracking

For questions or issues, check the logs at `logs/google_drive_sync.log` or run with `--verbose` flag for detailed output.
