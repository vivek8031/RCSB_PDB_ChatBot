#!/usr/bin/env python3
"""
Google Drive Sync Manager

Orchestrates the entire Google Drive to RAGFlow knowledge base sync process.
Can be run as a standalone script or imported as a module.
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.google_drive_sync.config import (
    SyncConfig,
    SyncResults,
    setup_logging,
    RAGFlowSyncError
)
from src.google_drive_sync.drive_client import GoogleDriveClient
from src.google_drive_sync.spreadsheet_parser import SpreadsheetParser
from src.google_drive_sync.pdf_converter import PDFConverter
from src.google_drive_sync.document_downloader import DocumentDownloader
from src.google_drive_sync.change_detector import ChangeDetector


class GoogleDriveSyncManager:
    """Orchestrates the entire Google Drive sync process"""

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

        # Initialize components
        self.logger.info("Initializing components...")

        self.drive_client = GoogleDriveClient(
            credentials_path=config.credentials_path,
            token_path=config.token_path
        )

        self.spreadsheet_parser = SpreadsheetParser(
            drive_client=self.drive_client
        )

        self.pdf_converter = PDFConverter(
            converter_backend="playwright"  # Use Playwright for macOS compatibility
        )

        self.document_downloader = DocumentDownloader(
            drive_client=self.drive_client,
            pdf_converter=self.pdf_converter,
            output_dir=config.output_dir,
            max_file_size_mb=config.max_file_size_mb,
            timeout=config.download_timeout
        )

        self.change_detector = ChangeDetector(
            state_file=config.state_file
        )

        self.logger.info("✓ All components initialized")

    def sync(self) -> SyncResults:
        """
        Perform incremental sync (only downloads changed files)

        Returns:
            SyncResults with detailed sync information
        """
        start_time = datetime.now()
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("Starting Incremental Sync")
        self.logger.info("=" * 60)

        # Load previous sync state
        state = self.change_detector.load_state()

        # Check if this is first sync
        if self.change_detector.is_first_sync(state):
            self.logger.info("This is the first sync - performing full sync")
            return self.initial_sync()

        # Extract folder ID from URL
        folder_id = self.drive_client.extract_id_from_url(self.config.folder_url)
        if not folder_id:
            folder_id = self.config.folder_url  # Assume it's already an ID

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

        # Find spreadsheet
        spreadsheet_id = self.spreadsheet_parser.find_spreadsheet(folder_id)
        if not spreadsheet_id:
            error_msg = "No spreadsheet found in folder"
            self.logger.error(error_msg)
            return SyncResults(
                start_time=start_time.isoformat(),
                end_time=datetime.now().isoformat(),
                total_links=0,
                successful_downloads=0,
                failed_downloads=0,
                ragflow_sync_success=False,
                errors=[error_msg]
            )

        # Check if spreadsheet changed
        spreadsheet_changed = self.change_detector.detect_spreadsheet_changes(
            drive_client=self.drive_client,
            spreadsheet_id=spreadsheet_id,
            previous_md5=state.spreadsheet_md5
        )

        if not spreadsheet_changed:
            self.logger.info("No changes detected - sync complete")
            return SyncResults(
                start_time=start_time.isoformat(),
                end_time=datetime.now().isoformat(),
                total_links=0,
                successful_downloads=0,
                failed_downloads=0,
                ragflow_sync_success=True
            )

        # Spreadsheet changed - parse links
        self.logger.info("Spreadsheet changed - re-parsing links")
        links = self.spreadsheet_parser.parse_links_from_column(
            sheet_id=spreadsheet_id,
            column_index=1,  # Second column (0-indexed)
            skip_header=True
        )

        if not links:
            self.logger.warning("No valid links found in spreadsheet")

        # Download only changed/new files
        self.logger.info("")
        self.logger.info(f"Processing {len(links)} links...")
        self.logger.info("")

        successful_downloads = []
        failed_downloads = []
        errors = []

        for link in links:
            output_path = self.config.output_dir / link.filename

            # Check if file needs re-download
            if not self.change_detector.should_redownload(link, output_path, state):
                self.logger.info(f"[Row {link.row_number}] Skipping (unchanged): {link.filename}")
                continue

            # Download document
            result = self.document_downloader.download_document(link)

            if result.success:
                successful_downloads.append(result.path)
                # Update metadata
                self.change_detector.update_file_metadata(
                    state=state,
                    link=link,
                    local_path=result.path
                )
            else:
                failed_downloads.append((link.url, result.error or "Unknown error"))
                errors.append(f"Row {link.row_number}: {result.error}")

        # Clean up orphaned files
        self.logger.info("")
        self.change_detector.clean_orphaned_files(
            state=state,
            current_links=links,
            output_dir=self.config.output_dir
        )

        # Update state with new spreadsheet MD5 and page token
        state.spreadsheet_md5 = self.change_detector.get_current_spreadsheet_md5(
            drive_client=self.drive_client,
            spreadsheet_id=spreadsheet_id
        )

        # Get new page token for next sync
        _, new_token = self.change_detector.detect_drive_changes(
            drive_client=self.drive_client,
            folder_id=folder_id,
            previous_token=state.page_token
        )
        state.page_token = new_token

        # Save updated state
        self.change_detector.save_state(state)

        # Trigger RAGFlow sync if there were any changes
        ragflow_success = True
        if successful_downloads or failed_downloads:
            self.logger.info("")
            self.logger.info("=" * 60)
            self.logger.info("Triggering RAGFlow Sync")
            self.logger.info("=" * 60)
            ragflow_success = self.trigger_ragflow_sync()
        else:
            self.logger.info("No new files - skipping RAGFlow sync")

        # Generate results
        end_time = datetime.now()
        results = SyncResults(
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            total_links=len(links),
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

    def initial_sync(self) -> SyncResults:
        """
        Perform initial full sync (downloads all files)

        Returns:
            SyncResults with detailed sync information
        """
        start_time = datetime.now()
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("Starting Initial Full Sync")
        self.logger.info("=" * 60)

        # Create new state
        state = self.change_detector.load_state()

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

        # Find and parse spreadsheet
        spreadsheet_id = self.spreadsheet_parser.find_spreadsheet(folder_id)
        if not spreadsheet_id:
            error_msg = "No spreadsheet found in folder"
            self.logger.error(error_msg)
            return SyncResults(
                start_time=start_time.isoformat(),
                end_time=datetime.now().isoformat(),
                total_links=0,
                successful_downloads=0,
                failed_downloads=0,
                ragflow_sync_success=False,
                errors=[error_msg]
            )

        # Parse all links from spreadsheet
        links = self.spreadsheet_parser.parse_links_from_column(
            sheet_id=spreadsheet_id,
            column_index=1,  # Second column (0-indexed)
            skip_header=True
        )

        if not links:
            self.logger.warning("No valid links found in spreadsheet")

        # Log summary
        self.logger.info("")
        self.logger.info(self.spreadsheet_parser.get_link_summary(links))
        self.logger.info("")

        # Download all files
        self.logger.info(f"Downloading {len(links)} documents...")
        self.logger.info("")

        successful_downloads = []
        failed_downloads = []
        errors = []

        for link in links:
            result = self.document_downloader.download_document(link)

            if result.success:
                successful_downloads.append(result.path)
                # Update metadata
                self.change_detector.update_file_metadata(
                    state=state,
                    link=link,
                    local_path=result.path
                )
            else:
                failed_downloads.append((link.url, result.error or "Unknown error"))
                errors.append(f"Row {link.row_number}: {result.error}")

        # Initialize state for next sync
        state.spreadsheet_md5 = self.change_detector.get_current_spreadsheet_md5(
            drive_client=self.drive_client,
            spreadsheet_id=spreadsheet_id
        )
        state.page_token = self.drive_client.get_start_page_token()

        # Save state
        self.change_detector.save_state(state)

        # Trigger RAGFlow sync
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
            total_links=len(links),
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
        Trigger RAGFlow knowledge base sync by running initialize_dataset.py

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get path to initialize_dataset.py
            project_root = Path(__file__).parent.parent.parent
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
