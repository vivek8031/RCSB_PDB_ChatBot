"""
Spreadsheet Parser Module

Parses Google Sheets to extract document links from the second column.
Validates and classifies links into different types (Google Docs, PDFs, webpages).
"""

import re
import logging
from typing import List, Optional
from urllib.parse import urlparse

from .config import DocumentLink, LinkType, SpreadsheetParseError
from .drive_client import GoogleDriveClient, GOOGLE_SHEET_MIME


class SpreadsheetParser:
    """Parse spreadsheet and extract document links"""

    def __init__(self, drive_client: GoogleDriveClient):
        """
        Initialize spreadsheet parser

        Args:
            drive_client: Authenticated Google Drive client
        """
        self.drive_client = drive_client
        self.logger = logging.getLogger("google_drive_sync.spreadsheet_parser")

    def find_spreadsheet(self, folder_id: str) -> Optional[str]:
        """
        Find Google Sheet in the specified folder

        Args:
            folder_id: Google Drive folder ID

        Returns:
            Spreadsheet file ID or None if not found
        """
        try:
            files = self.drive_client.list_folder_files(folder_id)

            # Find first Google Sheet
            for file in files:
                if file.get("mimeType") == GOOGLE_SHEET_MIME:
                    sheet_id = file["id"]
                    sheet_name = file["name"]
                    self.logger.info(f"✓ Found spreadsheet: {sheet_name} ({sheet_id})")
                    return sheet_id

            self.logger.warning("No Google Sheet found in folder")
            return None
        except Exception as e:
            self.logger.error(f"Error finding spreadsheet: {e}")
            raise SpreadsheetParseError(f"Failed to find spreadsheet: {e}")

    def classify_link(self, url: str) -> LinkType:
        """
        Determine the type of document link

        Args:
            url: URL to classify

        Returns:
            LinkType enum value
        """
        url_lower = url.lower()

        # Google Docs
        if "docs.google.com/document" in url_lower:
            return LinkType.GOOGLE_DOC
        elif "docs.google.com/spreadsheets" in url_lower:
            return LinkType.GOOGLE_SHEET
        elif "docs.google.com/presentation" in url_lower:
            return LinkType.GOOGLE_SLIDE
        elif "drive.google.com/file" in url_lower:
            # Could be any Google Drive file - check if it's a doc
            if "/document/" in url_lower:
                return LinkType.GOOGLE_DOC
            # Assume it's a regular file (could be PDF)
            return LinkType.PDF if url_lower.endswith(".pdf") else LinkType.UNKNOWN

        # Direct PDF link
        elif url_lower.endswith(".pdf"):
            return LinkType.PDF

        # Webpage (anything else with valid URL scheme)
        elif url_lower.startswith("http://") or url_lower.startswith("https://"):
            return LinkType.WEBPAGE

        return LinkType.UNKNOWN

    def is_valid_url(self, url: str) -> bool:
        """
        Validate URL format

        Args:
            url: URL to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            result = urlparse(url)
            # Must have scheme (http/https) and netloc (domain)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except Exception:
            return False

    def sanitize_filename(self, url: str, row: int) -> str:
        """
        Generate safe filename from URL or use row number

        Args:
            url: Source URL
            row: Row number in spreadsheet

        Returns:
            Safe filename string
        """
        # Try to extract filename from URL
        try:
            parsed = urlparse(url)
            path = parsed.path

            # Get last part of path
            if path:
                filename = path.split('/')[-1]
                # Remove query parameters and clean
                filename = filename.split('?')[0]
                # Remove invalid characters
                filename = re.sub(r'[\\/:*?"<>|]+', '_', filename)

                if filename and not filename.startswith('.'):
                    # Ensure it has .pdf extension
                    if not filename.lower().endswith('.pdf'):
                        filename += '.pdf'
                    return filename
        except Exception:
            pass

        # Fallback: use row number
        return f"document_row_{row}.pdf"

    def parse_links_from_column(
        self,
        sheet_id: str,
        column_index: int = 1,
        skip_header: bool = True
    ) -> List[DocumentLink]:
        """
        Parse links from specified column (0-indexed)

        Args:
            sheet_id: Google Sheet file ID
            column_index: Column index to parse (default: 1 for second column)
            skip_header: Skip first row if True

        Returns:
            List of DocumentLink objects
        """
        try:
            # Download spreadsheet as CSV
            rows = self.drive_client.get_spreadsheet_as_csv(sheet_id)

            if not rows:
                self.logger.warning("Spreadsheet is empty")
                return []

            # Skip header row if requested
            start_row = 1 if skip_header else 0
            data_rows = rows[start_row:]

            self.logger.info(f"Parsing column {column_index + 1} from {len(data_rows)} rows")

            # Parse links with validation
            links = []
            errors = []

            for row_num, row in enumerate(data_rows, start=start_row + 1):
                # Check if column exists in this row
                if len(row) <= column_index:
                    self.logger.debug(f"Row {row_num}: Missing column {column_index + 1}")
                    continue

                url = row[column_index].strip()

                # Skip empty cells
                if not url:
                    self.logger.debug(f"Row {row_num}: Empty cell")
                    continue

                # Validate URL
                if not self.is_valid_url(url):
                    errors.append(f"Row {row_num}: Invalid URL '{url}'")
                    continue

                # Classify and create DocumentLink
                try:
                    link_type = self.classify_link(url)

                    if link_type == LinkType.UNKNOWN:
                        self.logger.warning(f"Row {row_num}: Unknown link type for '{url}'")

                    # Get title from first column if available
                    title = row[0].strip() if len(row) > 0 and row[0] else None

                    link = DocumentLink(
                        row_number=row_num,
                        url=url,
                        link_type=link_type,
                        filename=self.sanitize_filename(url, row_num),
                        title=title
                    )
                    links.append(link)
                    self.logger.debug(f"Row {row_num}: {link}")
                except Exception as e:
                    errors.append(f"Row {row_num}: Error processing '{url}': {e}")

            # Log parsing summary
            if errors:
                self.logger.warning(f"Parsing completed with {len(errors)} errors")
                for error in errors[:10]:  # Show first 10 errors
                    self.logger.warning(f"  - {error}")
                if len(errors) > 10:
                    self.logger.warning(f"  ... and {len(errors) - 10} more errors")

            self.logger.info(f"✓ Parsed {len(links)} valid links from spreadsheet")

            # Log link type distribution
            type_counts = {}
            for link in links:
                type_name = link.link_type.value
                type_counts[type_name] = type_counts.get(type_name, 0) + 1

            self.logger.info(f"Link types: {dict(type_counts)}")

            return links

        except Exception as e:
            self.logger.error(f"Failed to parse spreadsheet {sheet_id}: {e}")
            raise SpreadsheetParseError(f"Failed to parse spreadsheet: {e}")

    def extract_google_drive_id(self, url: str) -> Optional[str]:
        """
        Extract file/folder ID from Google Drive URL

        Args:
            url: Google Drive URL

        Returns:
            Extracted ID or None
        """
        return self.drive_client.extract_id_from_url(url)

    def get_link_summary(self, links: List[DocumentLink]) -> str:
        """
        Generate a summary report of parsed links

        Args:
            links: List of DocumentLink objects

        Returns:
            Formatted summary string
        """
        if not links:
            return "No links found"

        # Count by type
        type_counts = {}
        for link in links:
            type_name = link.link_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        summary_parts = [
            f"Total Links: {len(links)}",
            "Breakdown by type:"
        ]

        for link_type, count in sorted(type_counts.items()):
            summary_parts.append(f"  - {link_type}: {count}")

        return "\n".join(summary_parts)
