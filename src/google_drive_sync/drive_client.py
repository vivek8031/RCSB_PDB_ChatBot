"""
Google Drive Client Module

Handles all Google Drive API interactions including OAuth authentication,
file listing, downloading, and change detection.
"""

import io
import re
import pickle
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

from .config import AuthenticationError, FolderNotFoundError


# OAuth scopes required for readonly access
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# MIME types
FOLDER_MIME = "application/vnd.google-apps.folder"
GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
GOOGLE_SHEET_MIME = "application/vnd.google-apps.spreadsheet"
GOOGLE_SLIDE_MIME = "application/vnd.google-apps.presentation"
GOOGLE_DRAWING_MIME = "application/vnd.google-apps.drawing"

# Exportable Google Workspace types
EXPORTABLE_TO_PDF = {
    GOOGLE_DOC_MIME: "application/pdf",
    GOOGLE_SHEET_MIME: "application/pdf",
    GOOGLE_SLIDE_MIME: "application/pdf",
    GOOGLE_DRAWING_MIME: "application/pdf",
}

# Patterns for extracting folder/file IDs from URLs
ID_PATTERNS = [
    r"drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)",
    r"drive\.google\.com/folderview\?id=([a-zA-Z0-9_-]+)",
    r"drive\.google\.com/file/d/([a-zA-Z0-9_-]+)",
    r"docs\.google\.com/document/d/([a-zA-Z0-9_-]+)",  # Google Docs
    r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)",  # Google Sheets
    r"docs\.google\.com/presentation/d/([a-zA-Z0-9_-]+)",  # Google Slides
    r"id=([a-zA-Z0-9_-]+)"
]


class GoogleDriveClient:
    """Handles all Google Drive API interactions"""

    def __init__(self, credentials_path: Path, token_path: Path):
        """
        Initialize Google Drive client with OAuth credentials

        Args:
            credentials_path: Path to OAuth client secrets JSON
            token_path: Path to store/load OAuth token
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.creds: Optional[Credentials] = None
        self.service = None
        self.logger = logging.getLogger("google_drive_sync.drive_client")

        # Authenticate and build service
        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate with Google Drive API using OAuth 2.0"""
        # Try to load existing token
        if self.token_path.exists():
            try:
                with open(self.token_path, 'rb') as token_file:
                    self.creds = pickle.load(token_file)
                self.logger.info("Loaded existing OAuth token")
            except Exception as e:
                self.logger.warning(f"Failed to load token: {e}")
                self.creds = None

        # Check if credentials are valid
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.logger.info("Refreshing expired OAuth token...")
                    self.creds.refresh(Request())
                    self.logger.info("✓ Token refreshed successfully")
                except Exception as e:
                    self.logger.error(f"Failed to refresh token: {e}")
                    raise AuthenticationError(
                        f"Failed to refresh credentials: {e}\n"
                        "Run: python scripts/setup_google_drive.py"
                    )
            else:
                raise AuthenticationError(
                    "No valid credentials found. "
                    "Run: python scripts/setup_google_drive.py"
                )

            # Save refreshed credentials
            self._save_credentials()

        # Build Drive API service
        try:
            self.service = build("drive", "v3", credentials=self.creds)
            self.logger.info("✓ Google Drive API service initialized")
        except Exception as e:
            raise AuthenticationError(f"Failed to initialize Drive API: {e}")

    def _save_credentials(self) -> None:
        """Save credentials to token file"""
        try:
            # Ensure parent directory exists
            self.token_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

            # Save token
            with open(self.token_path, 'wb') as token_file:
                pickle.dump(self.creds, token_file)

            # Set restrictive permissions (owner read/write only)
            self.token_path.chmod(0o600)
            self.logger.info(f"✓ Credentials saved to {self.token_path}")
        except Exception as e:
            self.logger.error(f"Failed to save credentials: {e}")

    def extract_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract file/folder ID from Google Drive URL

        Args:
            url: Google Drive URL

        Returns:
            Extracted ID or None if not found
        """
        for pattern in ID_PATTERNS:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_file_metadata(self, file_id: str, fields: Optional[str] = None) -> Dict[str, Any]:
        """
        Get file metadata from Google Drive

        Args:
            file_id: Google Drive file ID
            fields: Comma-separated list of fields to retrieve

        Returns:
            File metadata dictionary
        """
        if fields is None:
            fields = "id,name,mimeType,size,md5Checksum,modifiedTime,parents"

        try:
            metadata = self.service.files().get(
                fileId=file_id,
                fields=fields,
                supportsAllDrives=True
            ).execute()
            return metadata
        except HttpError as e:
            self.logger.error(f"Failed to get metadata for file {file_id}: {e}")
            raise

    def verify_folder(self, folder_id: str) -> Dict[str, Any]:
        """
        Verify that the given ID is a folder and accessible

        Args:
            folder_id: Google Drive folder ID

        Returns:
            Folder metadata

        Raises:
            FolderNotFoundError: If not a folder or not accessible
        """
        try:
            metadata = self.get_file_metadata(folder_id, fields="id,name,mimeType")

            if metadata.get("mimeType") != FOLDER_MIME:
                raise FolderNotFoundError(
                    f"ID '{folder_id}' is not a folder (type: {metadata.get('mimeType')})"
                )

            self.logger.info(f"✓ Verified folder: {metadata['name']} ({folder_id})")
            return metadata
        except HttpError as e:
            if e.resp.status == 404:
                raise FolderNotFoundError(f"Folder not found: {folder_id}")
            elif e.resp.status == 403:
                raise FolderNotFoundError(f"Access denied to folder: {folder_id}")
            else:
                raise FolderNotFoundError(f"Failed to access folder {folder_id}: {e}")

    def list_folder_files(self, folder_id: str) -> List[Dict[str, Any]]:
        """
        List all files in a folder (non-recursive)

        Args:
            folder_id: Google Drive folder ID

        Returns:
            List of file metadata dictionaries
        """
        files = []
        query = f"'{folder_id}' in parents and trashed=false"
        page_token = None

        try:
            while True:
                response = self.service.files().list(
                    q=query,
                    fields="nextPageToken, files(id,name,mimeType,size,md5Checksum,modifiedTime)",
                    pageSize=1000,
                    pageToken=page_token,
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                    corpora="allDrives"
                ).execute()

                files.extend(response.get("files", []))
                page_token = response.get("nextPageToken")

                if not page_token:
                    break

            self.logger.info(f"✓ Found {len(files)} files in folder {folder_id}")
            return files
        except HttpError as e:
            self.logger.error(f"Failed to list files in folder {folder_id}: {e}")
            raise

    def get_changes(self, page_token: str, folder_id: Optional[str] = None) -> Tuple[List[Dict], str]:
        """
        Get changes since the given page token

        Args:
            page_token: Token from previous changes request
            folder_id: Optional folder ID to filter changes

        Returns:
            Tuple of (list of changes, new page token)
        """
        changes = []
        new_page_token = page_token

        try:
            while True:
                response = self.service.changes().list(
                    pageToken=new_page_token,
                    fields="nextPageToken, newStartPageToken, changes(fileId,removed,file(id,name,mimeType,parents,md5Checksum,modifiedTime))",
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True
                ).execute()

                for change in response.get("changes", []):
                    # If folder_id specified, only include changes for files in that folder
                    if folder_id:
                        file_data = change.get("file", {})
                        parents = file_data.get("parents", [])
                        if folder_id in parents or change.get("removed"):
                            changes.append(change)
                    else:
                        changes.append(change)

                new_page_token = response.get("nextPageToken")
                if not new_page_token:
                    # Get the token for next time
                    new_page_token = response.get("newStartPageToken", page_token)
                    break

            self.logger.info(f"✓ Found {len(changes)} changes since last sync")
            return changes, new_page_token
        except HttpError as e:
            self.logger.error(f"Failed to get changes: {e}")
            raise

    def get_start_page_token(self) -> str:
        """
        Get the starting page token for change tracking

        Returns:
            Page token string
        """
        try:
            response = self.service.changes().getStartPageToken(
                supportsAllDrives=True
            ).execute()
            token = response.get("startPageToken")
            self.logger.info(f"✓ Got start page token: {token}")
            return token
        except HttpError as e:
            self.logger.error(f"Failed to get start page token: {e}")
            raise

    def download_file(self, file_id: str, output_path: Path) -> None:
        """
        Download a blob file (non-Google Workspace file)

        Args:
            file_id: Google Drive file ID
            output_path: Local path to save file
        """
        try:
            request = self.service.files().get_media(
                fileId=file_id,
                supportsAllDrives=True
            )

            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    self.logger.debug(f"  Download progress: {progress}%")

            # Write to file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(buffer.getvalue())

            self.logger.info(f"✓ Downloaded: {output_path.name}")
        except HttpError as e:
            self.logger.error(f"Failed to download file {file_id}: {e}")
            raise

    def export_to_pdf(self, file_id: str, output_path: Path) -> None:
        """
        Export Google Workspace file to PDF

        Args:
            file_id: Google Drive file ID
            output_path: Local path to save PDF
        """
        try:
            request = self.service.files().export_media(
                fileId=file_id,
                mimeType="application/pdf"
            )

            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    self.logger.debug(f"  Export progress: {progress}%")

            # Write to file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(buffer.getvalue())

            self.logger.info(f"✓ Exported to PDF: {output_path.name}")
        except HttpError as e:
            self.logger.error(f"Failed to export file {file_id} to PDF: {e}")
            raise

    def get_spreadsheet_as_csv(self, file_id: str) -> List[List[str]]:
        """
        Download Google Sheet and parse as CSV

        Args:
            file_id: Google Sheet file ID

        Returns:
            List of rows, where each row is a list of cell values
        """
        try:
            # Export as CSV
            request = self.service.files().export_media(
                fileId=file_id,
                mimeType="text/csv"
            )

            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            # Parse CSV
            import csv
            csv_data = buffer.getvalue().decode('utf-8')
            reader = csv.reader(io.StringIO(csv_data))
            rows = list(reader)

            self.logger.info(f"✓ Downloaded spreadsheet: {len(rows)} rows")
            return rows
        except HttpError as e:
            self.logger.error(f"Failed to download spreadsheet {file_id}: {e}")
            raise

    def is_google_workspace_file(self, mime_type: str) -> bool:
        """Check if file is a Google Workspace file"""
        return mime_type.startswith("application/vnd.google-apps.")

    def is_exportable_to_pdf(self, mime_type: str) -> bool:
        """Check if Google Workspace file can be exported to PDF"""
        return mime_type in EXPORTABLE_TO_PDF
