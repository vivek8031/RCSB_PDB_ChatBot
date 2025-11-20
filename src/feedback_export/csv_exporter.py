"""
CSV Exporter with Google Drive Upload

Simple CSV export that uploads to Google Drive using existing Drive API credentials.
No Google Sheets API required.
"""

import csv
import logging
import pickle
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from .config import QAPair, SPREADSHEET_HEADERS


class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


class CSVExporter:
    """Exports Q&A pairs to CSV and uploads to Google Drive"""

    def __init__(self, credentials_path: Path, token_path: Path, exports_dir: Path):
        """
        Initialize CSV exporter

        Args:
            credentials_path: Path to OAuth client secrets JSON
            token_path: Path to OAuth token
            exports_dir: Directory to save CSV files before upload
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.exports_dir = exports_dir
        self.creds: Credentials = None
        self.drive_service = None
        self.logger = logging.getLogger("feedback_export.csv_exporter")

        # Ensure exports directory exists
        self.exports_dir.mkdir(parents=True, exist_ok=True)

        # Authenticate
        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate with Google Drive API"""
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
        if self.creds and not self.creds.valid:
            if self.creds.expired and self.creds.refresh_token:
                try:
                    self.logger.info("Refreshing expired OAuth token...")
                    self.creds.refresh(Request())
                    self.logger.info("✓ Token refreshed successfully")
                    self._save_credentials()
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

        # Build Drive API service
        try:
            self.drive_service = build("drive", "v3", credentials=self.creds)
            self.logger.info("✓ Google Drive API service initialized")
        except Exception as e:
            raise AuthenticationError(f"Failed to initialize Drive API: {e}")

    def _save_credentials(self) -> None:
        """Save credentials to token file"""
        try:
            self.token_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with open(self.token_path, 'wb') as token_file:
                pickle.dump(self.creds, token_file)
            self.token_path.chmod(0o600)
            self.logger.info(f"✓ Credentials saved to {self.token_path}")
        except Exception as e:
            self.logger.error(f"Failed to save credentials: {e}")

    def write_csv(self, qa_pairs: List[QAPair], filename: str = None) -> Path:
        """
        Write Q&A pairs to CSV file

        Args:
            qa_pairs: List of QAPair objects
            filename: Optional filename (auto-generated if not provided or empty)

        Returns:
            Path to created CSV file
        """
        if not filename:  # Handle both None and empty string
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            filename = f"feedback_export_{timestamp}.csv"

        csv_path = self.exports_dir / filename

        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # Write headers
                writer.writerow(SPREADSHEET_HEADERS)

                # Write data rows
                for pair in qa_pairs:
                    writer.writerow(pair.to_row())

            self.logger.info(f"✓ Created CSV file: {csv_path}")
            self.logger.info(f"  Rows: {len(qa_pairs)} Q&A pairs")
            return csv_path

        except Exception as e:
            self.logger.error(f"Failed to write CSV: {e}")
            raise

    def upload_to_drive(
        self,
        csv_path: Path,
        folder_id: str = None,
        convert_to_sheets: bool = True
    ) -> Dict[str, str]:
        """
        Upload CSV file to Google Drive

        Args:
            csv_path: Path to CSV file to upload
            folder_id: Optional folder ID to upload to
            convert_to_sheets: Convert to Google Sheets format (default: True)

        Returns:
            Dict with 'id' and 'url' of uploaded file
        """
        try:
            # Prepare file metadata
            file_metadata = {
                'name': csv_path.stem,  # Filename without extension
            }

            # Add parent folder if specified
            if folder_id:
                file_metadata['parents'] = [folder_id]

            # Convert to Google Sheets if requested
            if convert_to_sheets:
                file_metadata['mimeType'] = 'application/vnd.google-apps.spreadsheet'

            # Upload file
            media = MediaFileUpload(
                str(csv_path),
                mimetype='text/csv',
                resumable=True
            )

            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()

            file_id = file.get('id')
            file_url = file.get('webViewLink')

            self.logger.info(f"✓ Uploaded to Google Drive")
            self.logger.info(f"  File ID: {file_id}")
            self.logger.info(f"  URL: {file_url}")

            return {
                'id': file_id,
                'url': file_url
            }

        except HttpError as e:
            self.logger.error(f"Failed to upload to Drive: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during upload: {e}")
            raise

    def export_and_upload(
        self,
        qa_pairs: List[QAPair],
        filename: str = None,
        folder_id: str = None
    ) -> Dict[str, Any]:
        """
        Complete export: write CSV and upload to Drive

        Args:
            qa_pairs: List of QAPair objects
            filename: Optional filename
            folder_id: Optional Drive folder ID

        Returns:
            Dict with export information (csv_path, drive_url, etc.)
        """
        # Write CSV locally
        csv_path = self.write_csv(qa_pairs, filename)

        # Upload to Drive
        drive_result = self.upload_to_drive(csv_path, folder_id)

        return {
            'csv_path': str(csv_path),
            'drive_id': drive_result['id'],
            'drive_url': drive_result['url'],
            'rows_exported': len(qa_pairs)
        }
