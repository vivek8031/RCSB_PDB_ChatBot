#!/usr/bin/env python3
"""
Preview Export Data

Shows what data will be exported to Google Sheets without actually uploading.
Useful for reviewing the data before export.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.feedback_export.config import ExportConfig
from src.feedback_export.conversation_extractor import ConversationExtractor


def preview_data():
    """Preview export data without uploading"""
    print("=" * 80)
    print("PREVIEW: Feedback Export Data")
    print("=" * 80)
    print()

    # Load configuration
    config = ExportConfig.from_env()

    # Create extractor
    extractor = ConversationExtractor(config.user_data_dir)

    # Extract Q&A pairs
    print("📊 Extracting Q&A pairs from user sessions...")
    print()
    qa_pairs = extractor.get_all_qa_pairs()

    if not qa_pairs:
        print("❌ No Q&A pairs found to export.")
        return

    print(f"✓ Found {len(qa_pairs)} Q&A pairs")
    print()
    print("=" * 80)

    # Group by user
    users = {}
    for pair in qa_pairs:
        if pair.user_id not in users:
            users[pair.user_id] = []
        users[pair.user_id].append(pair)

    # Display preview
    for user_id, user_pairs in users.items():
        print()
        print(f"👤 USER: {user_id}")
        print(f"   Total Q&A pairs: {len(user_pairs)}")
        print()

        for i, pair in enumerate(user_pairs[:3], 1):  # Show first 3 per user
            print(f"   [{i}] {pair.chat_title}")
            print(f"       Question: {pair.user_question[:100]}{'...' if len(pair.user_question) > 100 else ''}")
            print(f"       Answer: {pair.ai_response[:100]}{'...' if len(pair.ai_response) > 100 else ''}")

            if pair.feedback_rating:
                print(f"       Feedback: {pair.feedback_rating}")
                if pair.feedback_categories:
                    print(f"       Categories: {', '.join(pair.feedback_categories)}")
                if pair.feedback_comment:
                    print(f"       Comment: {pair.feedback_comment[:80]}{'...' if len(pair.feedback_comment) > 80 else ''}")

            if pair.referenced_documents:
                print(f"       References: {', '.join(pair.referenced_documents[:3])}{'...' if len(pair.referenced_documents) > 3 else ''}")

            print()

        if len(user_pairs) > 3:
            print(f"   ... and {len(user_pairs) - 3} more Q&A pairs")
            print()

    print("=" * 80)
    print()
    print("📋 SPREADSHEET PREVIEW:")
    print()
    print("When exported, the Google Sheet will have these columns:")
    print()
    print("| Export ID | User ID | Chat Title | Question Time | User Question |")
    print("| Answer Time | AI Response | Feedback Rating | Categories | Comment |")
    print("| Feedback Time | Referenced Documents | [Hidden: Message ID] |")
    print()
    print(f"Total rows to export: {len(qa_pairs)}")
    print()
    print("=" * 80)
    print()
    print("📍 WHERE THE SHEET WILL BE CREATED:")
    print()

    if config.spreadsheet_id:
        print(f"   Existing spreadsheet: {config.spreadsheet_id}")
        print("   New data will be APPENDED to this spreadsheet")
    else:
        print(f"   New spreadsheet will be created: '{config.spreadsheet_name}'")

    if config.folder_id:
        print(f"   In Google Drive folder: {config.folder_id}")
    else:
        print("   In your Google Drive root folder (My Drive)")

    print()
    print("=" * 80)
    print()
    print("✓ Preview complete!")
    print()
    print("To export this data to Google Sheets, run:")
    print("  python scripts/export_feedback_to_drive.py")
    print()


if __name__ == "__main__":
    preview_data()
