"""
Feedback Export Manager

Orchestrates the complete export process: extracting conversations and
uploading to Google Drive as CSV.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.feedback_export.config import (
    ExportConfig,
    ExportResults,
    setup_logging
)
from src.feedback_export.conversation_extractor import ConversationExtractor
from src.feedback_export.csv_exporter import CSVExporter


class FeedbackExportManager:
    """Manages the complete feedback export process"""

    def __init__(self, config: Optional[ExportConfig] = None):
        """
        Initialize export manager

        Args:
            config: ExportConfig object (loads from env if None)
        """
        # Load configuration
        if config is None:
            config = ExportConfig.from_env()
        self.config = config

        # Setup logging
        self.logger = setup_logging(log_level=config.log_level)

        self.logger.info("=" * 60)
        self.logger.info("Feedback Export Manager Initialized")
        self.logger.info("=" * 60)

        # Initialize components
        self.extractor = ConversationExtractor(config.user_data_dir)
        self.csv_exporter = CSVExporter(
            credentials_path=config.credentials_path,
            token_path=config.token_path,
            exports_dir=config.exports_dir
        )

        self.logger.info("✓ All components initialized")

    def export(self) -> ExportResults:
        """
        Perform complete export process

        Returns:
            ExportResults with detailed export information
        """
        start_time = datetime.now()
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("Starting Feedback Export")
        self.logger.info("=" * 60)

        errors = []

        try:
            # Step 1: Extract Q&A pairs
            self.logger.info("")
            self.logger.info("Step 1: Extracting Q&A pairs from user sessions")
            self.logger.info("-" * 60)

            all_qa_pairs = self.extractor.get_all_qa_pairs()

            if not all_qa_pairs:
                self.logger.warning("No Q&A pairs found to export")
                return ExportResults(
                    start_time=start_time.isoformat(),
                    end_time=datetime.now().isoformat(),
                    total_qa_pairs=0,
                    csv_path="",
                    drive_url="",
                    errors=["No Q&A pairs found to export"]
                )

            # Step 2: Export to CSV and upload to Drive
            self.logger.info("")
            self.logger.info("Step 2: Creating CSV and uploading to Google Drive")
            self.logger.info("-" * 60)

            export_result = self.csv_exporter.export_and_upload(
                qa_pairs=all_qa_pairs,
                filename=self.config.filename,
                folder_id=self.config.folder_id
            )

            # Generate results
            end_time = datetime.now()
            results = ExportResults(
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                total_qa_pairs=len(all_qa_pairs),
                csv_path=export_result['csv_path'],
                drive_url=export_result['drive_url'],
                errors=errors
            )

            # Log summary
            self.logger.info("")
            self.logger.info(results.to_summary())

            return results

        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            import traceback
            traceback.print_exc()

            return ExportResults(
                start_time=start_time.isoformat(),
                end_time=datetime.now().isoformat(),
                total_qa_pairs=0,
                csv_path="",
                drive_url="",
                errors=[str(e)]
            )


def main():
    """Main entry point for command-line execution"""
    try:
        # Create export manager
        manager = FeedbackExportManager()

        # Perform export
        results = manager.export()

        # Exit with appropriate code
        if results.errors:
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
