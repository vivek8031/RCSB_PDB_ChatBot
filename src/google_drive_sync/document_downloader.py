"""
Document Downloader Module

Downloads documents from various sources:
- Google Drive (Docs, Sheets, Slides, PDFs)
- Direct PDF URLs
- Web pages (converted to PDF)
"""

import logging
import requests
from pathlib import Path
from typing import Optional

from .config import (
    DocumentLink,
    LinkType,
    DownloadResult,
    DocumentDownloadError
)
from .drive_client import GoogleDriveClient
from .pdf_converter import PDFConverter


class DocumentDownloader:
    """Download documents from various sources"""

    def __init__(
        self,
        drive_client: GoogleDriveClient,
        pdf_converter: PDFConverter,
        output_dir: Path,
        max_file_size_mb: int = 100,
        timeout: int = 300
    ):
        """
        Initialize document downloader

        Args:
            drive_client: Authenticated Google Drive client
            pdf_converter: PDF converter instance
            output_dir: Directory to save downloaded files
            max_file_size_mb: Maximum file size to download (in MB)
            timeout: Download timeout in seconds
        """
        self.drive_client = drive_client
        self.pdf_converter = pdf_converter
        self.output_dir = output_dir
        self.max_file_size_mb = max_file_size_mb
        self.timeout = timeout
        self.logger = logging.getLogger("google_drive_sync.document_downloader")

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download_document(self, link: DocumentLink) -> DownloadResult:
        """
        Download document based on link type

        Args:
            link: DocumentLink object

        Returns:
            DownloadResult with success status and file path
        """
        output_path = self.output_dir / link.filename
        self.logger.info(f"[Row {link.row_number}] Downloading: {link.url}")
        self.logger.debug(f"  Type: {link.link_type.value}, Output: {link.filename}")

        try:
            if link.link_type == LinkType.GOOGLE_DOC:
                success = self.download_google_doc(link.url, output_path)
            elif link.link_type == LinkType.GOOGLE_SHEET:
                success = self.download_google_sheet(link.url, output_path)
            elif link.link_type == LinkType.GOOGLE_SLIDE:
                success = self.download_google_slide(link.url, output_path)
            elif link.link_type == LinkType.PDF:
                success = self.download_direct_pdf(link.url, output_path)
            elif link.link_type == LinkType.WEBPAGE:
                success = self.download_webpage_as_pdf(link.url, output_path)
            else:
                self.logger.warning(f"Unknown link type: {link.link_type}")
                success = self.download_webpage_as_pdf(link.url, output_path)

            if success:
                self.logger.info(f"✓ [{link.row_number}] Success: {link.filename}")
                return DownloadResult(success=True, path=output_path, link=link)
            else:
                error_msg = f"Download failed (method returned False)"
                self.logger.error(f"✗ [{link.row_number}] {error_msg}")
                return DownloadResult(success=False, error=error_msg, link=link)

        except Exception as e:
            error_msg = f"Download exception: {str(e)}"
            self.logger.error(f"✗ [{link.row_number}] {error_msg}")
            return DownloadResult(success=False, error=error_msg, link=link)

    def download_google_doc(self, url: str, output_path: Path) -> bool:
        """
        Download Google Doc and export as PDF

        Args:
            url: Google Docs URL
            output_path: Local path to save PDF

        Returns:
            True if successful
        """
        try:
            # Extract file ID from URL
            file_id = self.drive_client.extract_id_from_url(url)
            if not file_id:
                self.logger.error(f"Could not extract file ID from: {url}")
                return False

            # Get file metadata
            metadata = self.drive_client.get_file_metadata(file_id)
            mime_type = metadata.get("mimeType")

            self.logger.debug(f"Google file type: {mime_type}")

            # Check if it's a Google Workspace file that can be exported
            if self.drive_client.is_google_workspace_file(mime_type):
                if self.drive_client.is_exportable_to_pdf(mime_type):
                    # Export to PDF
                    self.drive_client.export_to_pdf(file_id, output_path)
                    return True
                else:
                    self.logger.error(f"Cannot export {mime_type} to PDF")
                    return False
            else:
                # It's a regular file, download it
                self.drive_client.download_file(file_id, output_path)
                return True

        except Exception as e:
            self.logger.error(f"Failed to download Google Doc: {e}")
            return False

    def download_google_sheet(self, url: str, output_path: Path) -> bool:
        """
        Download Google Sheet and export as PDF

        Args:
            url: Google Sheets URL
            output_path: Local path to save PDF

        Returns:
            True if successful
        """
        # Same logic as Google Doc
        return self.download_google_doc(url, output_path)

    def download_google_slide(self, url: str, output_path: Path) -> bool:
        """
        Download Google Slides and export as PDF

        Args:
            url: Google Slides URL
            output_path: Local path to save PDF

        Returns:
            True if successful
        """
        # Same logic as Google Doc
        return self.download_google_doc(url, output_path)

    def download_direct_pdf(self, url: str, output_path: Path) -> bool:
        """
        Download PDF from direct URL

        Args:
            url: Direct PDF URL
            output_path: Local path to save PDF

        Returns:
            True if successful
        """
        try:
            headers = {
                "User-Agent": self.pdf_converter.user_agent
            }

            # Stream download for large files
            with requests.get(url, headers=headers, timeout=self.timeout, stream=True, verify=True) as response:
                response.raise_for_status()

                # Check content type
                content_type = response.headers.get("Content-Type", "")
                if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
                    self.logger.warning(f"URL may not be a PDF (Content-Type: {content_type})")

                # Check file size
                content_length = response.headers.get("Content-Length")
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    if size_mb > self.max_file_size_mb:
                        self.logger.error(
                            f"File too large: {size_mb:.1f} MB (max: {self.max_file_size_mb} MB)"
                        )
                        return False

                # Download
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'wb') as f:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            # Check size during download
                            if downloaded > self.max_file_size_mb * 1024 * 1024:
                                self.logger.error(f"Download exceeded size limit")
                                return False

                file_size = output_path.stat().st_size
                self.logger.debug(f"Downloaded PDF: {file_size:,} bytes")
                return True

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to download PDF from {url}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error downloading PDF: {e}")
            return False

    def download_webpage_as_pdf(self, url: str, output_path: Path) -> bool:
        """
        Download webpage and convert to PDF

        Args:
            url: Webpage URL
            output_path: Local path to save PDF

        Returns:
            True if successful
        """
        try:
            # Use PDF converter to convert webpage to PDF
            success = self.pdf_converter.webpage_to_pdf(url, output_path)

            if not success:
                self.logger.error(f"Failed to convert webpage to PDF: {url}")
                # Save failure info
                self._save_failure_info(url, output_path)

            return success

        except Exception as e:
            self.logger.error(f"Failed to convert webpage {url}: {e}")
            self._save_failure_info(url, output_path)
            return False

    def _save_failure_info(self, url: str, intended_path: Path) -> None:
        """
        Save information about failed conversions

        Args:
            url: URL that failed to convert
            intended_path: Where the file would have been saved
        """
        try:
            failed_dir = Path("failed_conversions")
            failed_dir.mkdir(exist_ok=True)

            # Save failure info
            info_file = failed_dir / f"{intended_path.stem}_failure.txt"
            with open(info_file, 'w') as f:
                f.write(f"URL: {url}\n")
                f.write(f"Intended path: {intended_path}\n")
                f.write(f"Failure: PDF conversion failed\n")
                f.write(f"\nPlease manually review this URL and convert if needed.\n")

            self.logger.info(f"Failure info saved to: {info_file}")
        except Exception as e:
            self.logger.error(f"Failed to save failure info: {e}")

    def verify_pdf(self, file_path: Path) -> bool:
        """
        Verify that a file is a valid PDF

        Args:
            file_path: Path to PDF file

        Returns:
            True if valid PDF
        """
        try:
            # Check file exists and is not empty
            if not file_path.exists() or file_path.stat().st_size == 0:
                return False

            # Check PDF magic bytes
            with open(file_path, 'rb') as f:
                header = f.read(4)
                return header == b'%PDF'
        except Exception:
            return False
