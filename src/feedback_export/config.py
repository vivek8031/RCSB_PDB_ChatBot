"""
Configuration for Feedback Export Module

Manages configuration loading from environment variables and defines
data structures for export results.
"""

import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class ExportConfig:
    """Configuration for feedback export"""

    # Google Drive settings
    credentials_path: Path
    token_path: Path
    folder_id: Optional[str] = None

    # Export settings
    filename: Optional[str] = None  # Auto-generated if None
    exports_dir: Path = Path("exports")

    # Data source
    user_data_dir: Path = Path("user_data")

    # Logging
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "ExportConfig":
        """Load configuration from environment variables"""

        # Get project root
        project_root = Path(__file__).parent.parent.parent

        # Credentials paths (reuse from Google Drive sync)
        credentials_path_str = os.getenv(
            "GOOGLE_DRIVE_CREDENTIALS_PATH",
            "credentials/google_drive_credentials.json"
        )
        token_path_str = os.getenv(
            "GOOGLE_DRIVE_TOKEN_PATH",
            "credentials/google_drive_token.pickle"
        )

        # Resolve paths (support both absolute and relative)
        if os.path.isabs(credentials_path_str):
            credentials_path = Path(os.path.expanduser(credentials_path_str))
        else:
            credentials_path = project_root / credentials_path_str

        if os.path.isabs(token_path_str):
            token_path = Path(os.path.expanduser(token_path_str))
        else:
            token_path = project_root / token_path_str

        # User data directory
        user_data_dir_str = os.getenv("USER_DATA_DIR", "user_data")
        if os.path.isabs(user_data_dir_str):
            user_data_dir = Path(user_data_dir_str)
        else:
            user_data_dir = project_root / user_data_dir_str

        # Export settings
        folder_id = os.getenv("GOOGLE_DRIVE_EXPORT_FOLDER_ID")
        filename = os.getenv("FEEDBACK_EXPORT_FILENAME")  # None = auto-generate

        exports_dir_str = os.getenv("FEEDBACK_EXPORT_DIR", "exports")
        if os.path.isabs(exports_dir_str):
            exports_dir = Path(exports_dir_str)
        else:
            exports_dir = project_root / exports_dir_str

        # Logging
        log_level = os.getenv("LOG_LEVEL", "INFO")

        return cls(
            credentials_path=credentials_path,
            token_path=token_path,
            folder_id=folder_id,
            filename=filename,
            exports_dir=exports_dir,
            user_data_dir=user_data_dir,
            log_level=log_level
        )


@dataclass
class QAPair:
    """A single question-answer interaction with optional feedback"""

    # IDs
    export_id: str
    message_id: str  # Assistant message ID (for deduplication)

    # Context
    user_id: str
    chat_title: str

    # Question
    question_timestamp: str
    user_question: str

    # Answer
    answer_timestamp: str
    ai_response: str

    # Feedback (optional)
    feedback_rating: Optional[str] = None  # "thumbs-up" or "thumbs-down"
    feedback_categories: List[str] = field(default_factory=list)
    feedback_comment: Optional[str] = None
    feedback_timestamp: Optional[str] = None

    # References
    referenced_documents: List[str] = field(default_factory=list)

    def to_row(self) -> List[str]:
        """Convert to spreadsheet row format"""
        return [
            self.export_id,
            self.user_id,
            self.chat_title,
            self.question_timestamp,
            self.user_question,
            self.answer_timestamp,
            self.ai_response,
            self._format_rating(),
            ", ".join(self.feedback_categories) if self.feedback_categories else "",
            self.feedback_comment or "",
            self.feedback_timestamp or "",
            ", ".join(self.referenced_documents) if self.referenced_documents else "",
            self.message_id  # Hidden column for deduplication
        ]

    def _format_rating(self) -> str:
        """Format rating for spreadsheet display"""
        if not self.feedback_rating:
            return ""
        if self.feedback_rating == "thumbs-up":
            return "👍 Positive"
        elif self.feedback_rating == "thumbs-down":
            return "👎 Negative"
        return self.feedback_rating


@dataclass
class ExportResults:
    """Results from an export operation"""

    start_time: str
    end_time: str
    total_qa_pairs: int
    csv_path: str
    drive_url: str
    errors: List[str] = field(default_factory=list)

    def to_summary(self) -> str:
        """Generate human-readable summary"""
        duration = self._calculate_duration()

        summary = [
            "",
            "=" * 60,
            "Feedback Export Summary",
            "=" * 60,
            f"Start time: {self.start_time}",
            f"End time: {self.end_time}",
            f"Duration: {duration}",
            "",
            f"✓ Q&A pairs exported: {self.total_qa_pairs}",
            f"✓ CSV file: {self.csv_path}",
            "",
            f"Google Drive URL: {self.drive_url}",
        ]

        if self.errors:
            summary.extend([
                "",
                f"Errors encountered: {len(self.errors)}",
            ])
            for error in self.errors:
                summary.append(f"  - {error}")

        summary.append("=" * 60)
        return "\n".join(summary)

    def _calculate_duration(self) -> str:
        """Calculate duration between start and end time"""
        try:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            duration = end - start
            seconds = duration.total_seconds()

            if seconds < 60:
                return f"{seconds:.1f} seconds"
            elif seconds < 3600:
                return f"{seconds/60:.1f} minutes"
            else:
                return f"{seconds/3600:.1f} hours"
        except Exception:
            return "Unknown"


# Spreadsheet column headers
SPREADSHEET_HEADERS = [
    "Export ID",
    "User ID",
    "Chat Title",
    "Question Timestamp",
    "User Question",
    "Answer Timestamp",
    "AI Response",
    "Feedback Rating",
    "Feedback Categories",
    "Feedback Comment",
    "Feedback Timestamp",
    "Referenced Documents",
    "Message ID"  # Hidden column
]


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Setup logging configuration"""

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Create logger for this module
    logger = logging.getLogger("feedback_export")
    logger.setLevel(getattr(logging, log_level.upper()))

    return logger
