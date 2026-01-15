"""
Google Drive Sync Configuration Module

Provides configuration dataclasses and logging setup for the Google Drive
synchronization system.
"""

import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
from logging.handlers import RotatingFileHandler


class LinkType(Enum):
    """Types of document links found in spreadsheet"""
    GOOGLE_DOC = "google_doc"
    GOOGLE_SHEET = "google_sheet"
    GOOGLE_SLIDE = "google_slide"
    PDF = "pdf"
    WEBPAGE = "webpage"
    UNKNOWN = "unknown"


@dataclass
class SyncConfig:
    """Main configuration for Google Drive sync"""
    folder_url: str
    output_dir: Path
    credentials_path: Path
    token_path: Path
    sync_interval: int = 3600  # seconds
    max_file_size_mb: int = 100
    download_timeout: int = 300  # seconds
    enable_notifications: bool = False
    state_file: Path = field(default_factory=lambda: Path(".gdrive_sync_state.json"))
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "SyncConfig":
        """Load configuration from environment variables"""
        folder_url = os.getenv("GOOGLE_DRIVE_FOLDER_URL")
        if not folder_url:
            raise ValueError(
                "GOOGLE_DRIVE_FOLDER_URL not set in environment. "
                "Please configure .env file."
            )

        # Get project root directory (3 levels up from this file)
        project_root = Path(__file__).parent.parent.parent

        # K8s-friendly paths - relative to project root
        credentials_path_str = os.getenv(
            "GOOGLE_DRIVE_CREDENTIALS_PATH",
            "credentials/google_drive_credentials.json"
        )

        # Support both absolute and relative paths
        if os.path.isabs(credentials_path_str):
            credentials_path = Path(os.path.expanduser(credentials_path_str))
        else:
            credentials_path = project_root / credentials_path_str

        token_path_str = os.getenv(
            "GOOGLE_DRIVE_TOKEN_PATH",
            "credentials/google_drive_token.pickle"
        )

        if os.path.isabs(token_path_str):
            token_path = Path(os.path.expanduser(token_path_str))
        else:
            token_path = project_root / token_path_str

        # Validate credentials exist
        if not credentials_path.exists():
            raise FileNotFoundError(
                f"Credentials file not found: {credentials_path}\n"
                "Please place your OAuth credentials at: credentials/google_drive_credentials.json\n"
                "Or run: python scripts/setup_google_drive.py"
            )

        output_dir = project_root / "knowledge_base"

        return cls(
            folder_url=folder_url,
            output_dir=output_dir,
            credentials_path=credentials_path,
            token_path=token_path,
            sync_interval=int(os.getenv("GOOGLE_DRIVE_SYNC_INTERVAL", "3600")),
            max_file_size_mb=int(os.getenv("GOOGLE_DRIVE_MAX_FILE_SIZE_MB", "100")),
            download_timeout=int(os.getenv("GOOGLE_DRIVE_DOWNLOAD_TIMEOUT", "300")),
            enable_notifications=os.getenv("GOOGLE_DRIVE_ENABLE_NOTIFICATIONS", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )

    def __repr__(self) -> str:
        """Redact sensitive information in logs"""
        return (
            f"SyncConfig(folder_url='{self.folder_url[:50]}...', "
            f"output_dir={self.output_dir}, credentials=<redacted>)"
        )


@dataclass
class DocumentLink:
    """Represents a document link found in spreadsheet"""
    row_number: int
    url: str
    link_type: LinkType
    filename: str
    title: Optional[str] = None

    def __repr__(self) -> str:
        return f"DocumentLink(row={self.row_number}, type={self.link_type.value}, filename='{self.filename}')"


@dataclass
class FileMetadata:
    """Metadata for a downloaded file"""
    drive_id: Optional[str]
    local_path: str
    size: int
    md5: Optional[str]
    download_time: str
    source_url: str


@dataclass
class SyncState:
    """State tracking for incremental sync"""
    page_token: Optional[str] = None
    last_sync: Optional[str] = None
    spreadsheet_md5: Optional[str] = None
    downloaded_files: Dict[str, FileMetadata] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "page_token": self.page_token,
            "last_sync": self.last_sync,
            "spreadsheet_md5": self.spreadsheet_md5,
            "downloaded_files": {
                k: {
                    "drive_id": v.drive_id,
                    "local_path": v.local_path,
                    "size": v.size,
                    "md5": v.md5,
                    "download_time": v.download_time,
                    "source_url": v.source_url
                }
                for k, v in self.downloaded_files.items()
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyncState":
        """Create from dictionary"""
        downloaded_files = {}
        for k, v in data.get("downloaded_files", {}).items():
            downloaded_files[k] = FileMetadata(**v)

        return cls(
            page_token=data.get("page_token"),
            last_sync=data.get("last_sync"),
            spreadsheet_md5=data.get("spreadsheet_md5"),
            downloaded_files=downloaded_files
        )


@dataclass
class DownloadResult:
    """Result of a document download operation"""
    success: bool
    path: Optional[Path] = None
    error: Optional[str] = None
    link: Optional[DocumentLink] = None


@dataclass
class SyncResults:
    """Comprehensive results from a sync operation"""
    start_time: str
    end_time: str
    total_links: int
    successful_downloads: int
    failed_downloads: int
    ragflow_sync_success: bool
    errors: List[str] = field(default_factory=list)
    downloaded_files: List[Path] = field(default_factory=list)
    failed_files: List[tuple] = field(default_factory=list)  # (url, error)

    def to_log_summary(self) -> str:
        """Generate human-readable summary for logging"""
        from datetime import datetime

        try:
            start_dt = datetime.fromisoformat(self.start_time)
            end_dt = datetime.fromisoformat(self.end_time)
            duration = (end_dt - start_dt).total_seconds()
        except:
            duration = 0

        success_rate = (
            (self.successful_downloads / self.total_links * 100)
            if self.total_links > 0 else 0
        )

        summary_parts = [
            "\n" + "="*60,
            "Google Drive Sync Report",
            "="*60,
            f"Start Time: {self.start_time}",
            f"End Time: {self.end_time}",
            f"Duration: {duration:.1f} seconds",
            "",
            "Results:",
            f"  Total Links: {self.total_links}",
            f"  Successful: {self.successful_downloads}",
            f"  Failed: {self.failed_downloads}",
            f"  Success Rate: {success_rate:.1f}%",
            "",
            f"RAGFlow Sync: {'✓ Success' if self.ragflow_sync_success else '✗ Failed'}",
        ]

        if self.downloaded_files:
            summary_parts.extend([
                "",
                "Downloaded Files:",
                *[f"  - {f.name}" for f in self.downloaded_files]
            ])

        if self.failed_files:
            summary_parts.extend([
                "",
                "Failed Files:",
                *[f"  - {url}: {error}" for url, error in self.failed_files]
            ])

        if self.errors:
            summary_parts.extend([
                "",
                "Errors:",
                *[f"  - {e}" for e in self.errors]
            ])
        else:
            summary_parts.extend(["", "Errors:", "  None"])

        summary_parts.append("="*60)
        return "\n".join(summary_parts)


def setup_logging(log_level: str = "INFO", log_to_file: bool = True) -> logging.Logger:
    """
    Configure comprehensive logging for Google Drive sync

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Whether to log to file in addition to console

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("google_drive_sync")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler - for interactive runs
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler - rotating logs (10MB max, keep 5 backups)
    if log_to_file:
        try:
            # Try /tmp first (works in K8s containers), fallback to local logs/
            log_file = Path("/tmp/logs/google_drive_sync.log")
            log_file.parent.mkdir(exist_ok=True)
        except PermissionError:
            try:
                log_file = Path("logs/google_drive_sync.log")
                log_file.parent.mkdir(exist_ok=True)
            except PermissionError:
                # Skip file logging if we can't write anywhere
                logger.warning("Cannot create log directory, skipping file logging")
                return logger

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    return logger


# Custom exceptions for better error handling

class GoogleDriveSyncError(Exception):
    """Base exception for sync errors"""
    pass


class AuthenticationError(GoogleDriveSyncError):
    """OAuth/authentication failures"""
    pass


class FolderNotFoundError(GoogleDriveSyncError):
    """Drive folder doesn't exist or not accessible"""
    pass


class SpreadsheetParseError(GoogleDriveSyncError):
    """Failed to parse spreadsheet"""
    pass


class DocumentDownloadError(GoogleDriveSyncError):
    """Failed to download document"""
    pass


class PDFConversionError(GoogleDriveSyncError):
    """Failed to convert to PDF"""
    pass


class RAGFlowSyncError(GoogleDriveSyncError):
    """Failed to sync with RAGFlow"""
    pass
