"""
Change Detector Module

Detects changes in Google Drive folder and tracks sync state.
Uses Google Drive Changes API for efficient change detection.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from .config import SyncState, FileMetadata, DocumentLink
from .drive_client import GoogleDriveClient


class ChangeDetector:
    """Detect changes in Google Drive folder and spreadsheet"""

    def __init__(self, state_file: Path = Path(".gdrive_sync_state.json")):
        """
        Initialize change detector

        Args:
            state_file: Path to state file for tracking sync history
        """
        self.state_file = state_file
        self.logger = logging.getLogger("google_drive_sync.change_detector")

    def load_state(self) -> SyncState:
        """
        Load previous sync state from file

        Returns:
            SyncState object (empty if no previous state)
        """
        if not self.state_file.exists():
            self.logger.info("No previous sync state found")
            return SyncState()

        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)

            state = SyncState.from_dict(data)
            self.logger.info(f"✓ Loaded sync state (last sync: {state.last_sync})")
            return state
        except Exception as e:
            self.logger.error(f"Failed to load sync state: {e}")
            return SyncState()

    def save_state(self, state: SyncState) -> None:
        """
        Save current sync state to file

        Args:
            state: SyncState object to save
        """
        try:
            # Update last sync time
            state.last_sync = datetime.now().isoformat()

            # Ensure parent directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            # Save to file
            with open(self.state_file, 'w') as f:
                json.dump(state.to_dict(), f, indent=2)

            self.logger.info(f"✓ Saved sync state to {self.state_file}")
        except Exception as e:
            self.logger.error(f"Failed to save sync state: {e}")

    def is_first_sync(self, state: SyncState) -> bool:
        """
        Check if this is the first sync

        Args:
            state: Current sync state

        Returns:
            True if first sync
        """
        return state.page_token is None or state.last_sync is None

    def detect_spreadsheet_changes(
        self,
        drive_client: GoogleDriveClient,
        spreadsheet_id: str,
        previous_md5: Optional[str]
    ) -> bool:
        """
        Detect if spreadsheet has changed by comparing MD5 checksum

        Args:
            drive_client: Google Drive client
            spreadsheet_id: Google Sheet file ID
            previous_md5: Previous MD5 checksum

        Returns:
            True if spreadsheet has changed or this is first check
        """
        try:
            # Get current metadata
            metadata = drive_client.get_file_metadata(
                spreadsheet_id,
                fields="id,name,md5Checksum,modifiedTime"
            )

            current_md5 = metadata.get("md5Checksum")
            modified_time = metadata.get("modifiedTime")

            # First time or no previous MD5
            if not previous_md5:
                self.logger.info("First spreadsheet check (no previous MD5)")
                return True

            # Compare MD5
            if current_md5 != previous_md5:
                self.logger.info(
                    f"✓ Spreadsheet changed (modified: {modified_time})"
                )
                return True
            else:
                self.logger.info("Spreadsheet unchanged")
                return False

        except Exception as e:
            self.logger.error(f"Failed to check spreadsheet changes: {e}")
            # On error, assume it changed to be safe
            return True

    def get_current_spreadsheet_md5(
        self,
        drive_client: GoogleDriveClient,
        spreadsheet_id: str
    ) -> Optional[str]:
        """
        Get current MD5 checksum of spreadsheet

        Args:
            drive_client: Google Drive client
            spreadsheet_id: Google Sheet file ID

        Returns:
            MD5 checksum string or None if failed
        """
        try:
            metadata = drive_client.get_file_metadata(
                spreadsheet_id,
                fields="md5Checksum"
            )
            return metadata.get("md5Checksum")
        except Exception as e:
            self.logger.error(f"Failed to get spreadsheet MD5: {e}")
            return None

    def detect_drive_changes(
        self,
        drive_client: GoogleDriveClient,
        folder_id: str,
        previous_token: Optional[str]
    ) -> tuple[List[dict], str]:
        """
        Detect changes in Drive folder using Changes API

        Args:
            drive_client: Google Drive client
            folder_id: Folder ID to monitor
            previous_token: Previous page token

        Returns:
            Tuple of (list of changes, new page token)
        """
        try:
            # If no previous token, get starting token
            if not previous_token:
                self.logger.info("First sync - getting initial page token")
                new_token = drive_client.get_start_page_token()
                return [], new_token

            # Get changes since last token
            changes, new_token = drive_client.get_changes(previous_token, folder_id)

            if changes:
                self.logger.info(f"✓ Detected {len(changes)} changes in folder")
                for change in changes[:5]:  # Log first 5
                    file_data = change.get("file", {})
                    name = file_data.get("name", "unknown")
                    if change.get("removed"):
                        self.logger.debug(f"  - Removed: {name}")
                    else:
                        self.logger.debug(f"  - Modified: {name}")
                if len(changes) > 5:
                    self.logger.debug(f"  ... and {len(changes) - 5} more")
            else:
                self.logger.info("No changes detected in folder")

            return changes, new_token

        except Exception as e:
            self.logger.error(f"Failed to detect drive changes: {e}")
            # Return empty changes and keep old token on error
            return [], previous_token or ""

    def should_redownload(
        self,
        link: DocumentLink,
        local_file: Path,
        state: SyncState
    ) -> bool:
        """
        Determine if a file should be re-downloaded

        Args:
            link: DocumentLink object
            local_file: Path to local file
            state: Current sync state

        Returns:
            True if file should be re-downloaded
        """
        # If local file doesn't exist, download it
        if not local_file.exists():
            self.logger.debug(f"{link.filename}: File doesn't exist locally")
            return True

        # Check if we have metadata for this file
        file_key = link.filename
        if file_key not in state.downloaded_files:
            self.logger.debug(f"{link.filename}: No metadata in state")
            return True

        metadata = state.downloaded_files[file_key]

        # Check if URL changed
        if metadata.source_url != link.url:
            self.logger.debug(f"{link.filename}: URL changed")
            return True

        # Check if local file size changed (may indicate corruption)
        current_size = local_file.stat().st_size
        if metadata.size != current_size:
            self.logger.debug(f"{link.filename}: Size mismatch")
            return True

        # File exists and metadata matches - no need to redownload
        self.logger.debug(f"{link.filename}: Up to date")
        return False

    def update_file_metadata(
        self,
        state: SyncState,
        link: DocumentLink,
        local_path: Path,
        drive_id: Optional[str] = None
    ) -> None:
        """
        Update file metadata in sync state

        Args:
            state: Sync state to update
            link: DocumentLink object
            local_path: Path to downloaded file
            drive_id: Google Drive file ID (if applicable)
        """
        try:
            file_size = local_path.stat().st_size

            metadata = FileMetadata(
                drive_id=drive_id,
                local_path=str(local_path),
                size=file_size,
                md5=None,  # Could calculate MD5 if needed
                download_time=datetime.now().isoformat(),
                source_url=link.url
            )

            state.downloaded_files[link.filename] = metadata
            self.logger.debug(f"Updated metadata for {link.filename}")
        except Exception as e:
            self.logger.error(f"Failed to update metadata for {link.filename}: {e}")

    def clean_orphaned_files(
        self,
        state: SyncState,
        current_links: List[DocumentLink],
        output_dir: Path
    ) -> int:
        """
        Remove files that are no longer in the spreadsheet

        Args:
            state: Current sync state
            current_links: List of current document links
            output_dir: Directory containing downloaded files

        Returns:
            Number of files removed
        """
        current_filenames = {link.filename for link in current_links}
        removed_count = 0

        # Check files in state
        for filename in list(state.downloaded_files.keys()):
            if filename not in current_filenames:
                # File is no longer in spreadsheet
                file_path = output_dir / filename

                # Remove from disk
                if file_path.exists():
                    try:
                        file_path.unlink()
                        self.logger.info(f"✓ Removed orphaned file: {filename}")
                        removed_count += 1
                    except Exception as e:
                        self.logger.error(f"Failed to remove {filename}: {e}")

                # Remove from state
                del state.downloaded_files[filename]

        if removed_count > 0:
            self.logger.info(f"✓ Cleaned up {removed_count} orphaned files")

        return removed_count
