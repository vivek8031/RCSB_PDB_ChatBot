#!/bin/bash
################################################################################
# Google Drive to RAGFlow Knowledge Base Sync Script
#
# This script is designed to run as a cron job to automatically sync documents
# from Google Drive to the local knowledge base and trigger RAGFlow sync.
#
# Usage:
#   ./scripts/sync_google_drive.sh
#
# Cron example (hourly):
#   0 * * * * /path/to/chatbot_ui_v2/scripts/sync_google_drive.sh
#
################################################################################

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/google_drive_sync.log"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON="$VENV_DIR/bin/python"

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "ERROR: Virtual environment not found at $VENV_DIR" >&2
    echo "Please create it with: python3 -m venv .venv" >&2
    exit 1
fi

# Check if Python interpreter exists
if [ ! -f "$PYTHON" ]; then
    echo "ERROR: Python interpreter not found at $PYTHON" >&2
    exit 1
fi

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Log with timestamp
log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

# Log separator
log_separator() {
    echo "$(printf '=%.0s' {1..80})" | tee -a "$LOG_FILE"
}

# Main execution
main() {
    log_separator
    log "INFO" "Google Drive Sync Started"
    log_separator

    # Change to project directory
    cd "$PROJECT_DIR" || {
        log "ERROR" "Failed to change to project directory: $PROJECT_DIR"
        exit 1
    }

    log "INFO" "Project directory: $PROJECT_DIR"
    log "INFO" "Log file: $LOG_FILE"

    # Check if .env file exists
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        log "ERROR" ".env file not found!"
        log "ERROR" "Please create .env file with Google Drive configuration"
        exit 1
    fi

    # Activate virtual environment (though not strictly needed for direct python calls)
    log "INFO" "Using Python: $PYTHON"

    # Run the sync
    log "INFO" "Starting Google Drive sync..."
    "$PYTHON" -m src.google_drive_sync.sync_manager 2>&1 | while IFS= read -r line; do
        # Forward output to log file
        echo "$line" | tee -a "$LOG_FILE"
    done

    # Capture exit code
    EXIT_CODE="${PIPESTATUS[0]}"

    # Log result
    if [ $EXIT_CODE -eq 0 ]; then
        log "INFO" "✓ Sync completed successfully"
    else
        log "ERROR" "✗ Sync failed with exit code $EXIT_CODE"

        # Optional: Send notification on failure
        # Uncomment and configure based on your notification system
        # send_notification "Google Drive sync failed with exit code $EXIT_CODE"
    fi

    log_separator
    log "INFO" "Google Drive Sync Complete"
    log_separator
    echo "" >> "$LOG_FILE"

    exit $EXIT_CODE
}

# Optional: Notification function (customize for your needs)
send_notification() {
    local message="$1"

    # Example: Send email (requires mailutils or sendmail)
    # echo "$message" | mail -s "Google Drive Sync Alert" admin@example.com

    # Example: Send to Slack webhook
    # curl -X POST -H 'Content-type: application/json' \
    #     --data "{\"text\":\"$message\"}" \
    #     "$SLACK_WEBHOOK_URL"

    # Example: Log to syslog
    # logger -t google_drive_sync "$message"

    # For now, just log
    log "WARN" "Notification: $message"
}

# Run main function
main "$@"
