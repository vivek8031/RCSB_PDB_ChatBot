#!/bin/bash
#
# Export user feedback to Google Sheets
# Cron-friendly wrapper script
#

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project directory
cd "$PROJECT_ROOT"

# Setup logging
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/feedback_export_$(date +%Y%m%d_%H%M%S).log"

echo "===========================================================" | tee -a "$LOG_FILE"
echo "Feedback Export - $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "===========================================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Activate virtual environment if exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..." | tee -a "$LOG_FILE"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "Activating virtual environment..." | tee -a "$LOG_FILE"
    source .venv/bin/activate
fi

# Run export
echo "Running feedback export..." | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

python3 "$SCRIPT_DIR/export_feedback_to_drive.py" 2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}

echo "" | tee -a "$LOG_FILE"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ Export completed successfully" | tee -a "$LOG_FILE"
else
    echo "✗ Export failed with exit code $EXIT_CODE" | tee -a "$LOG_FILE"
fi

echo "===========================================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

exit $EXIT_CODE
