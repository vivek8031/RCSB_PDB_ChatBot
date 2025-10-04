#!/usr/bin/env python3
"""
PDF Type Detection Test Script
Detects whether PDFs are text-based or scanned/image-based using dual validation:
1. Text extraction length check
2. Character validity check (ordinal ranges for a-z, A-Z, 0-9)
"""

import os
import sys
from pathlib import Path
from typing import Dict, Tuple, List

try:
    import fitz  # PyMuPDF
except ImportError:
    print("❌ ERROR: PyMuPDF not installed")
    print("Please install: pip install pymupdf")
    sys.exit(1)


def is_valid_char(char: str) -> bool:
    """
    Check if character is readable (a-z, A-Z, 0-9, space, common punctuation)

    Uses Python ord() to check character ordinal ranges:
    - A-Z: 65-90
    - a-z: 97-122
    - 0-9: 48-57
    - Space and basic punctuation: 32-47, 58-64, 91-96, 123-126
    - Newlines: 10, 13
    """
    o = ord(char)
    return (
        (65 <= o <= 90) or      # A-Z
        (97 <= o <= 122) or     # a-z
        (48 <= o <= 57) or      # 0-9
        (32 <= o <= 47) or      # space and basic punctuation
        (58 <= o <= 64) or      # :;<=>?@
        (91 <= o <= 96) or      # [\]^_`
        (123 <= o <= 126) or    # {|}~
        o == 10 or o == 13      # newlines (LF, CR)
    )


def analyze_text_quality(text: str) -> Tuple[int, float]:
    """
    Analyze text quality and calculate valid character percentage

    Args:
        text: Extracted text from PDF page

    Returns:
        Tuple of (total_chars, valid_percentage)
    """
    total_chars = len(text)
    if total_chars == 0:
        return 0, 0.0

    valid_chars = sum(1 for char in text if is_valid_char(char))
    valid_percentage = (valid_chars / total_chars) * 100

    return total_chars, valid_percentage


def classify_page(char_count: int, valid_pct: float) -> Tuple[str, str]:
    """
    Classify a single page based on character count and validity

    Args:
        char_count: Number of characters extracted
        valid_pct: Percentage of valid characters (0-100)

    Returns:
        Tuple of (classification, emoji)
    """
    if char_count < 100:
        return "Empty/Image", "❌"
    elif valid_pct < 50:
        return "Corrupted/Garbled", "⚠️"
    elif valid_pct < 80:
        return "Low Quality", "⚠️"
    else:
        return "Text-based", "✅"


def analyze_pdf(pdf_path: Path) -> Dict:
    """
    Analyze a PDF file and determine if it's text-based or scanned

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dictionary with analysis results
    """
    try:
        doc = fitz.open(pdf_path)

        page_results = []
        total_chars = 0
        total_valid_chars = 0

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()

            char_count, valid_pct = analyze_text_quality(text)
            classification, emoji = classify_page(char_count, valid_pct)

            page_results.append({
                "page_num": page_num + 1,
                "char_count": char_count,
                "valid_pct": valid_pct,
                "classification": classification,
                "emoji": emoji
            })

            total_chars += char_count
            if char_count > 0:
                total_valid_chars += (char_count * valid_pct / 100)

        doc.close()

        # Calculate overall statistics
        num_pages = len(page_results)
        avg_chars_per_page = total_chars / num_pages if num_pages > 0 else 0
        overall_valid_pct = (total_valid_chars / total_chars * 100) if total_chars > 0 else 0

        # Count page types
        text_pages = sum(1 for p in page_results if p["classification"] == "Text-based")
        image_pages = sum(1 for p in page_results if p["classification"] == "Empty/Image")
        corrupted_pages = sum(1 for p in page_results if "Corrupted" in p["classification"] or "Low" in p["classification"])

        # Overall classification
        if text_pages >= num_pages * 0.9:
            overall_classification = "TEXT-BASED PDF"
            overall_emoji = "✅"
            recommendation = "Use 'naive' parser (NO OCR needed)"
        elif image_pages >= num_pages * 0.9:
            overall_classification = "SCANNED/IMAGE PDF"
            overall_emoji = "❌"
            recommendation = "Use 'DeepDOC' parser (OCR required)"
        else:
            overall_classification = "MIXED PDF"
            overall_emoji = "⚠️"
            recommendation = "Use 'DeepDOC' parser for scanned pages"

        return {
            "success": True,
            "filename": pdf_path.name,
            "num_pages": num_pages,
            "total_chars": total_chars,
            "avg_chars_per_page": avg_chars_per_page,
            "overall_valid_pct": overall_valid_pct,
            "text_pages": text_pages,
            "image_pages": image_pages,
            "corrupted_pages": corrupted_pages,
            "page_results": page_results,
            "overall_classification": overall_classification,
            "overall_emoji": overall_emoji,
            "recommendation": recommendation
        }

    except Exception as e:
        return {
            "success": False,
            "filename": pdf_path.name,
            "error": str(e)
        }


def main():
    """Main function to test all PDFs in knowledge base"""
    print("=" * 70)
    print("📄 PDF Type Detection Test Script")
    print("=" * 70)
    print("Dual Validation: Text Length + Character Validity (a-z, A-Z, 0-9)")
    print("=" * 70)
    print()

    # Get knowledge base directory (same directory as this script)
    kb_dir = Path(__file__).parent

    # Find all PDF files
    pdf_files = list(kb_dir.glob("*.pdf"))

    if not pdf_files:
        print("⚠️  No PDF files found in knowledge base directory")
        return

    print(f"Found {len(pdf_files)} PDF files to analyze\n")

    # Analyze each PDF
    results = []
    for pdf_path in sorted(pdf_files):
        print(f"📄 Testing: {pdf_path.name}")
        print("-" * 70)

        result = analyze_pdf(pdf_path)
        results.append(result)

        if not result["success"]:
            print(f"   ❌ Error: {result['error']}")
            print()
            continue

        # Display page-by-page results
        for page_info in result["page_results"]:
            print(f"   Page {page_info['page_num']:2d}: "
                  f"{page_info['char_count']:5d} chars | "
                  f"Valid: {page_info['valid_pct']:5.1f}% {page_info['emoji']} "
                  f"{page_info['classification']}")

        # Display overall statistics
        print()
        print(f"   📊 Overall Stats:")
        print(f"      - Total pages: {result['num_pages']}")
        print(f"      - Total chars: {result['total_chars']:,}")
        print(f"      - Avg chars/page: {result['avg_chars_per_page']:.0f}")
        print(f"      - Valid char %: {result['overall_valid_pct']:.1f}%")
        print(f"      - Text pages: {result['text_pages']}/{result['num_pages']}")
        print(f"      - Image pages: {result['image_pages']}/{result['num_pages']}")
        print(f"      - Corrupted pages: {result['corrupted_pages']}/{result['num_pages']}")
        print()
        print(f"   Classification: {result['overall_classification']} {result['overall_emoji']}")
        print(f"   Recommendation: {result['recommendation']}")
        print()

    # Summary
    print("=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)

    successful_results = [r for r in results if r["success"]]

    text_based_pdfs = sum(1 for r in successful_results if r["overall_classification"] == "TEXT-BASED PDF")
    scanned_pdfs = sum(1 for r in successful_results if r["overall_classification"] == "SCANNED/IMAGE PDF")
    mixed_pdfs = sum(1 for r in successful_results if r["overall_classification"] == "MIXED PDF")
    failed_pdfs = len(results) - len(successful_results)

    print(f"   Text-based PDFs: {text_based_pdfs} ✅")
    print(f"   Scanned/Image PDFs: {scanned_pdfs} ❌")
    print(f"   Mixed PDFs: {mixed_pdfs} ⚠️")
    if failed_pdfs > 0:
        print(f"   Failed to analyze: {failed_pdfs} ❌")
    print()

    # Overall recommendation
    if scanned_pdfs == 0 and mixed_pdfs == 0:
        print("✅ RECOMMENDATION: Use 'naive' parser (NO OCR needed)")
        print("   All PDFs are text-based with extractable text")
        print("   Change line 268 in initialize_dataset.py:")
        print('   "layout_recognize": "naive",  # Changed from "DeepDOC"')
    elif scanned_pdfs > 0:
        print("❌ RECOMMENDATION: Use 'DeepDOC' parser (OCR required)")
        print(f"   Found {scanned_pdfs} scanned/image PDFs that need OCR")
    else:
        print("⚠️  RECOMMENDATION: Use 'DeepDOC' parser for mixed content")
        print(f"   Found {mixed_pdfs} PDFs with mixed text/image pages")

    print("=" * 70)

    # Detailed file list
    print("\n📋 Detailed Results:")
    print("-" * 70)
    for result in successful_results:
        print(f"   {result['overall_emoji']} {result['filename']}: "
              f"{result['overall_classification']} "
              f"({result['text_pages']}/{result['num_pages']} text pages)")

    print("=" * 70)


if __name__ == "__main__":
    main()
