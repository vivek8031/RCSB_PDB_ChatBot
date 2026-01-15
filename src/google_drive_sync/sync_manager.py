#!/usr/bin/env python3
"""
Google Drive Sync Manager - Simplified

Downloads all files from a Google Drive folder directly to knowledge base.
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

# Add parent directory to path for imports (works in both local and Docker)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))  # For Docker where src/ is copied to /app

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from google_drive_sync.config import (
    SyncConfig,
    SyncResults,
    setup_logging,
)
from google_drive_sync.drive_client import GoogleDriveClient


class GoogleDriveSyncManager:
    """Downloads files directly from Google Drive folder"""

    def __init__(self, config: Optional[SyncConfig] = None):
        """
        Initialize sync manager

        Args:
            config: SyncConfig object (loads from env if None)
        """
        # Load configuration
        if config is None:
            config = SyncConfig.from_env()
        self.config = config

        # Setup logging
        self.logger = setup_logging(
            log_level=config.log_level,
            log_to_file=True
        )

        self.logger.info("=" * 60)
        self.logger.info("Google Drive Sync Manager Initialized")
        self.logger.info("=" * 60)

        # Initialize Google Drive client
        self.drive_client = GoogleDriveClient(
            credentials_path=config.credentials_path,
            token_path=config.token_path
        )

        self.logger.info("✓ All components initialized")

    def sync(self) -> SyncResults:
        """
        Download all files from Google Drive folder

        Returns:
            SyncResults with detailed sync information
        """
        start_time = datetime.now()
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("Starting Google Drive Sync")
        self.logger.info("=" * 60)

        # Extract folder ID
        folder_id = self.drive_client.extract_id_from_url(self.config.folder_url)
        if not folder_id:
            folder_id = self.config.folder_url

        # Verify folder
        try:
            self.drive_client.verify_folder(folder_id)
        except Exception as e:
            self.logger.error(f"Failed to access folder: {e}")
            return SyncResults(
                start_time=start_time.isoformat(),
                end_time=datetime.now().isoformat(),
                total_links=0,
                successful_downloads=0,
                failed_downloads=0,
                ragflow_sync_success=False,
                errors=[str(e)]
            )

        # List all files in folder
        self.logger.info("")
        all_files = self.drive_client.list_folder_files(folder_id)

        # Filter out spreadsheets (we only want documents and PDFs)
        files_to_download = [
            f for f in all_files
            if f['mimeType'] != 'application/vnd.google-apps.spreadsheet'
        ]

        self.logger.info(f"Found {len(files_to_download)} files to download (excluding spreadsheets)")
        self.logger.info("")

        # Download each file
        successful_downloads = []
        failed_downloads = []
        errors = []

        for file_metadata in files_to_download:
            file_id = file_metadata['id']
            file_name = file_metadata['name']
            mime_type = file_metadata['mimeType']

            self.logger.info(f"Downloading: {file_name}")

            try:
                # Determine output filename
                if self.drive_client.is_exportable_to_pdf(mime_type):
                    # Google Docs, Sheets, Slides -> export as PDF
                    output_name = f"{Path(file_name).stem}.pdf"
                    output_path = self.config.output_dir / output_name

                    self.drive_client.export_to_pdf(file_id, output_path)
                    self.logger.info(f"✓ Exported to PDF: {output_name}")
                    successful_downloads.append(output_path)

                elif mime_type == 'application/pdf':
                    # Already a PDF -> download directly
                    output_path = self.config.output_dir / file_name

                    self.drive_client.download_file(file_id, output_path)
                    self.logger.info(f"✓ Downloaded: {file_name}")
                    successful_downloads.append(output_path)

                else:
                    # Unsupported file type
                    self.logger.warning(f"⊘ Skipping unsupported type: {file_name} ({mime_type})")

            except Exception as e:
                error_msg = f"Failed to download {file_name}: {e}"
                self.logger.error(f"✗ {error_msg}")
                failed_downloads.append((file_name, str(e)))
                errors.append(error_msg)

        # Trigger RAGFlow sync if we downloaded anything
        ragflow_success = True
        if successful_downloads:
            self.logger.info("")
            self.logger.info("=" * 60)
            self.logger.info("Triggering RAGFlow Sync")
            self.logger.info("=" * 60)
            ragflow_success = self.trigger_ragflow_sync()

        # Generate results
        end_time = datetime.now()
        results = SyncResults(
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            total_links=len(files_to_download),
            successful_downloads=len(successful_downloads),
            failed_downloads=len(failed_downloads),
            ragflow_sync_success=ragflow_success,
            errors=errors,
            downloaded_files=successful_downloads,
            failed_files=failed_downloads
        )

        # Log summary
        self.logger.info("")
        self.logger.info(results.to_log_summary())

        return results

    def trigger_ragflow_sync(self) -> bool:
        """
        Trigger RAGFlow knowledge base sync

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get path to initialize_dataset.py
            # Detect container environment vs local development
            if os.path.exists("/app/knowledge_base"):
                # Running in container
                project_root = Path("/app")
            else:
                # Running locally
                project_root = Path(__file__).resolve().parent.parent.parent
            script_path = project_root / "knowledge_base" / "initialize_dataset.py"

            if not script_path.exists():
                self.logger.error(f"Script not found: {script_path}")
                return False

            self.logger.info(f"Running: {script_path} --sync")

            # Run the script
            result = subprocess.run(
                [sys.executable, str(script_path), "--sync"],
                cwd=script_path.parent,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            # Log output
            if result.stdout:
                self.logger.info("RAGFlow sync output:")
                for line in result.stdout.split('\n'):
                    if line.strip():
                        self.logger.info(f"  {line}")

            if result.returncode == 0:
                self.logger.info("✓ RAGFlow sync completed successfully")
                return True
            else:
                self.logger.error(f"✗ RAGFlow sync failed (exit code: {result.returncode})")
                if result.stderr:
                    self.logger.error("Error output:")
                    for line in result.stderr.split('\n'):
                        if line.strip():
                            self.logger.error(f"  {line}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("RAGFlow sync timed out after 10 minutes")
            return False
        except Exception as e:
            self.logger.error(f"Failed to trigger RAGFlow sync: {e}")
            return False


def main():
    """Main entry point for command-line execution"""
    try:
        # Create sync manager
        manager = GoogleDriveSyncManager()

        # Perform sync
        results = manager.sync()

        # Exit with appropriate code
        if results.failed_downloads > 0 or not results.ragflow_sync_success:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"FATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
