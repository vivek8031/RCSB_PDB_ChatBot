#!/usr/bin/env python3
"""
Export User Feedback to Google Sheets

Reads conversation data from user_data/ JSON files and exports to Google Sheets
with Q&A pairs, feedback, and AI response references.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.feedback_export.export_manager import FeedbackExportManager


def main():
    """Main entry point"""
    print("=" * 60)
    print("RCSB PDB ChatBot - Feedback Export to Google Sheets")
    print("=" * 60)
    print()

    try:
        # Create export manager
        manager = FeedbackExportManager()

        # Perform export
        results = manager.export()

        # Show results
        print()
        print("✓ Export completed successfully!")
        print()
        print(f"Local CSV: {results.csv_path}")
        print(f"Google Drive URL: {results.drive_url}")
        print()

        if results.errors:
            print("⚠ Errors encountered:")
            for error in results.errors:
                print(f"  - {error}")
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"✗ Export failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
