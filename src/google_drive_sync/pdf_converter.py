"""
PDF Converter Module

Converts HTML/web content to clean PDF using multiple backends:
- WeasyPrint (primary): Pure Python, good for static content
- Playwright (fallback): Browser-based, handles JavaScript
"""

import re
import logging
import requests
from pathlib import Path
from typing import Optional
from bs4 import BeautifulSoup

from .config import PDFConversionError


class PDFConverter:
    """Convert HTML/web content to PDF with multiple backends"""

    def __init__(self, converter_backend: str = "weasyprint", user_agent: Optional[str] = None):
        """
        Initialize PDF converter

        Args:
            converter_backend: Primary backend to use ("weasyprint" or "playwright")
            user_agent: Custom user agent string for requests
        """
        self.backend = converter_backend
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        self.logger = logging.getLogger("google_drive_sync.pdf_converter")

        # Check backend availability
        self._weasyprint_available = self._check_weasyprint()
        self._playwright_available = self._check_playwright()

        if not self._weasyprint_available and not self._playwright_available:
            raise PDFConversionError(
                "No PDF conversion backend available. "
                "Install weasyprint or playwright."
            )

    def _check_weasyprint(self) -> bool:
        """Check if WeasyPrint is available"""
        try:
            import weasyprint
            self.logger.debug("✓ WeasyPrint available")
            return True
        except (ImportError, OSError) as e:
            # OSError occurs when system libraries are missing (macOS/pyenv issue)
            self.logger.debug(f"✗ WeasyPrint not available: {e}")
            return False

    def _check_playwright(self) -> bool:
        """Check if Playwright is available"""
        try:
            from playwright.sync_api import sync_playwright
            self.logger.debug("✓ Playwright available")
            return True
        except ImportError:
            self.logger.debug("✗ Playwright not available")
            return False

    def fetch_html(self, url: str, timeout: int = 30) -> str:
        """
        Fetch HTML content from URL

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds

        Returns:
            HTML content as string
        """
        try:
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }

            response = requests.get(url, headers=headers, timeout=timeout, verify=True)
            response.raise_for_status()

            self.logger.debug(f"✓ Fetched HTML from {url} ({len(response.content)} bytes)")
            return response.text
        except Exception as e:
            self.logger.error(f"Failed to fetch HTML from {url}: {e}")
            raise

    def clean_html(self, html: str, remove_scripts: bool = True) -> str:
        """
        Clean HTML content by removing unwanted elements

        Args:
            html: HTML content
            remove_scripts: Remove script and style tags

        Returns:
            Cleaned HTML
        """
        try:
            soup = BeautifulSoup(html, 'lxml')

            if remove_scripts:
                # Remove script and style tags
                for tag in soup.find_all(['script', 'style', 'noscript', 'iframe']):
                    tag.decompose()

                # Remove common unwanted elements by tag
                for tag in soup.find_all(['header', 'footer', 'nav', 'aside']):
                    tag.decompose()

                # Remove elements with unwanted classes/IDs (more aggressive)
                unwanted_patterns = [
                    'header', 'footer', 'nav', 'navigation', 'navbar', 'sidebar',
                    'menu', 'ad', 'advertisement', 'ads', 'banner', 'popup', 'modal',
                    'cookie', 'consent', 'gdpr', 'privacy-notice',
                    'social', 'share', 'sharing',
                    'subscribe', 'newsletter', 'signup',
                    'comment', 'related', 'recommended',
                    'breadcrumb', 'pagination',
                    'masthead', 'site-header', 'site-footer',
                    'top-bar', 'bottom-bar', 'side-bar'
                ]

                # Remove by class
                for pattern in unwanted_patterns:
                    for tag in soup.find_all(class_=re.compile(pattern, re.I)):
                        tag.decompose()

                # Remove by ID
                for pattern in unwanted_patterns:
                    for tag in soup.find_all(id=re.compile(pattern, re.I)):
                        tag.decompose()

                # Remove elements with specific roles
                for role in ['banner', 'navigation', 'complementary', 'contentinfo']:
                    for tag in soup.find_all(attrs={'role': role}):
                        tag.decompose()

            # Get cleaned HTML
            cleaned = str(soup)
            self.logger.debug(f"✓ Cleaned HTML: {len(html)} → {len(cleaned)} bytes")
            return cleaned
        except Exception as e:
            self.logger.warning(f"HTML cleaning failed: {e}, using original")
            return html

    def html_to_pdf_weasyprint(
        self,
        html_content: str,
        output_path: Path,
        base_url: Optional[str] = None
    ) -> bool:
        """
        Convert HTML to PDF using WeasyPrint

        Args:
            html_content: HTML content string
            output_path: Path to save PDF
            base_url: Base URL for resolving relative links

        Returns:
            True if successful, False otherwise
        """
        if not self._weasyprint_available:
            return False

        try:
            from weasyprint import HTML, CSS

            # Custom CSS for continuous layout and better page breaks
            custom_css = CSS(string='''
                @page {
                    size: A4;
                    margin: 2cm 1.5cm;
                }
                body {
                    font-family: "Helvetica Neue", Arial, sans-serif;
                    font-size: 11pt;
                    line-height: 1.6;
                    color: #333;
                }
                h1, h2, h3, h4, h5, h6 {
                    page-break-after: avoid;
                    page-break-inside: avoid;
                    margin-top: 1.2em;
                    margin-bottom: 0.6em;
                }
                p {
                    orphans: 3;
                    widows: 3;
                }
                img {
                    max-width: 100%;
                    page-break-inside: avoid;
                }
                table {
                    page-break-inside: avoid;
                }
                pre, code {
                    page-break-inside: avoid;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }
                /* Minimize forced page breaks */
                * {
                    page-break-inside: avoid !important;
                }
            ''')

            # Create HTML object
            html_obj = HTML(string=html_content, base_url=base_url)

            # Render to PDF
            output_path.parent.mkdir(parents=True, exist_ok=True)
            html_obj.write_pdf(output_path, stylesheets=[custom_css])

            file_size = output_path.stat().st_size
            self.logger.info(f"✓ WeasyPrint: Created PDF ({file_size:,} bytes)")
            return True

        except Exception as e:
            self.logger.error(f"WeasyPrint conversion failed: {e}")
            return False

    def webpage_to_pdf_weasyprint(self, url: str, output_path: Path) -> bool:
        """
        Convert webpage to PDF using WeasyPrint

        Args:
            url: URL to convert
            output_path: Path to save PDF

        Returns:
            True if successful, False otherwise
        """
        if not self._weasyprint_available:
            return False

        try:
            # Fetch and clean HTML
            html = self.fetch_html(url)
            # Note: Keeping scripts for now, WeasyPrint ignores them anyway

            # Convert to PDF
            return self.html_to_pdf_weasyprint(html, output_path, base_url=url)

        except Exception as e:
            self.logger.error(f"WeasyPrint webpage conversion failed: {e}")
            return False

    def html_to_pdf_playwright(
        self,
        html_content: str,
        output_path: Path,
        wait_for_load: bool = True
    ) -> bool:
        """
        Convert HTML to PDF using Playwright (browser-based)

        Args:
            html_content: HTML content string
            output_path: Path to save PDF
            wait_for_load: Wait for page load before rendering

        Returns:
            True if successful, False otherwise
        """
        if not self._playwright_available:
            return False

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Set content
                page.set_content(html_content)

                if wait_for_load:
                    page.wait_for_load_state("networkidle", timeout=30000)

                # Generate PDF with optimized settings
                output_path.parent.mkdir(parents=True, exist_ok=True)
                page.pdf(
                    path=str(output_path),
                    format='A4',
                    print_background=True,
                    margin={
                        'top': '2cm',
                        'right': '1.5cm',
                        'bottom': '2cm',
                        'left': '1.5cm'
                    }
                )

                browser.close()

                file_size = output_path.stat().st_size
                self.logger.info(f"✓ Playwright: Created PDF ({file_size:,} bytes)")
                return True

        except Exception as e:
            self.logger.error(f"Playwright conversion failed: {e}")
            return False

    def webpage_to_pdf_playwright(self, url: str, output_path: Path) -> bool:
        """
        Convert webpage to PDF using Playwright

        Args:
            url: URL to convert
            output_path: Path to save PDF

        Returns:
            True if successful, False otherwise
        """
        if not self._playwright_available:
            return False

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Navigate to the actual URL (so all resources load properly)
                page.goto(url, wait_until="networkidle", timeout=60000)

                # Remove unwanted elements via JavaScript (AFTER page loads)
                page.evaluate('''() => {
                    // Remove unwanted elements
                    const selectorsToRemove = [
                        'header', 'footer', 'nav', 'aside',
                        '[role="banner"]', '[role="navigation"]', '[role="complementary"]', '[role="contentinfo"]',
                        '.header', '.footer', '.nav', '.navigation', '.navbar', '.sidebar', '.side-bar',
                        '.menu', '.ad', '.advertisement', '.ads', '.banner',
                        '.cookie', '.cookie-banner', '.cookie-consent', '.cookie-notice',
                        '.consent', '.gdpr', '.privacy-notice', '.privacy-banner',
                        '.social', '.social-share', '.social-sharing', '.share', '.sharing',
                        '.subscribe', '.newsletter', '.signup', '.sign-up',
                        '.comment', '.comments', '.related', '.recommended',
                        '.breadcrumb', '.breadcrumbs', '.pagination',
                        '.masthead', '.site-header', '.site-footer',
                        '.top-bar', '.bottom-bar',
                        '#header', '#footer', '#nav', '#navigation', '#sidebar',
                        '#cookie-banner', '#cookie-notice', '#consent-banner'
                    ];

                    selectorsToRemove.forEach(selector => {
                        try {
                            document.querySelectorAll(selector).forEach(el => el.remove());
                        } catch(e) {}
                    });

                    // Remove scripts and iframes
                    document.querySelectorAll('script, iframe, noscript').forEach(el => el.remove());
                }''')

                # Inject CSS to minimize page breaks
                page.add_style_tag(content='''
                    /* Minimize page breaks */
                    * {
                        page-break-inside: avoid !important;
                        break-inside: avoid !important;
                    }

                    h1, h2, h3, h4, h5, h6 {
                        page-break-after: avoid !important;
                        break-after: avoid !important;
                    }

                    p, li, table, figure {
                        page-break-inside: avoid !important;
                        orphans: 3;
                        widows: 3;
                    }

                    body {
                        font-size: 11pt;
                        line-height: 1.5;
                    }
                ''')

                # Generate PDF with print media emulation
                output_path.parent.mkdir(parents=True, exist_ok=True)
                page.emulate_media(media='print')
                page.pdf(
                    path=str(output_path),
                    format='A4',
                    print_background=False,
                    prefer_css_page_size=True,
                    margin={
                        'top': '1.5cm',
                        'right': '1.5cm',
                        'bottom': '1.5cm',
                        'left': '1.5cm'
                    }
                )

                browser.close()

                file_size = output_path.stat().st_size
                self.logger.info(f"✓ Playwright: Created PDF from {url} ({file_size:,} bytes)")
                return True

        except Exception as e:
            self.logger.error(f"Playwright webpage conversion failed: {e}")
            return False

    def webpage_to_pdf(self, url: str, output_path: Path) -> bool:
        """
        Convert webpage to PDF with automatic backend selection

        Tries WeasyPrint first, falls back to Playwright if it fails.

        Args:
            url: URL to convert
            output_path: Path to save PDF

        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Converting webpage to PDF: {url}")

        # Try WeasyPrint first (faster, no browser needed)
        if self.backend == "weasyprint" and self._weasyprint_available:
            self.logger.debug("Trying WeasyPrint...")
            if self.webpage_to_pdf_weasyprint(url, output_path):
                return True

            self.logger.warning("WeasyPrint failed, trying Playwright...")

        # Try Playwright
        if self._playwright_available:
            self.logger.debug("Trying Playwright...")
            if self.webpage_to_pdf_playwright(url, output_path):
                return True

        # If we haven't tried WeasyPrint yet, try it now
        if self.backend != "weasyprint" and self._weasyprint_available:
            self.logger.debug("Trying WeasyPrint as last resort...")
            if self.webpage_to_pdf_weasyprint(url, output_path):
                return True

        self.logger.error(f"All PDF conversion attempts failed for {url}")
        return False
