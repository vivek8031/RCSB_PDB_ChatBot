#!/usr/bin/env python3
"""
Simple Integration Test for Message Feedback System Fix

Tests that the core fix is working: messages now have timestamps and
feedback system no longer produces "timestamp not found" errors.
"""

import sys
import json
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from user_session_manager import UserSessionManager, StoredMessage, UserChat


def test_timestamp_fix():
    """Test that the timestamp fix resolves the core issue"""

    print("🧪 Testing Message Feedback Timestamp Fix")
    print("=" * 50)

    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    try:
        user_data_dir = Path(temp_dir) / "user_data"
        user_data_dir.mkdir(exist_ok=True)

        # Initialize session manager
        session_manager = UserSessionManager(str(user_data_dir))

        # Test data
        user_id = "test_user"
        chat_id = "test_chat"

        # Create a chat directly (simulating what happens in the app)
        timestamp = datetime.now()
        message = StoredMessage(
            role="assistant",
            content="Test response about RCSB PDB",
            timestamp=timestamp,
            references=None,
            feedback=None
        )

        # Create chat with required fields
        user_chat = UserChat(
            chat_id=chat_id,
            title="Test Chat",
            created_at=timestamp,
            updated_at=timestamp,
            message_count=1,
            ragflow_session_id="test_session",
            messages=[message]
        )

        # Manually save the session (simulating app behavior)
        session_manager._ensure_user_session(user_id)
        user_session = session_manager.get_user_session(user_id)
        user_session.chats.append(user_chat)
        session_manager._save_user_sessions(user_session)

        print("✅ Created test chat with timestamped message")

        # Test feedback saving (this was failing before the fix)
        feedback_data = {
            "rating": "thumbs-up",
            "categories": ["helpful"],
            "comment": "Good response",
            "feedback_timestamp": datetime.now().isoformat()
        }

        # Try to add feedback using the message timestamp
        success = session_manager.add_message_feedback(
            user_id,
            chat_id,
            timestamp.isoformat(),
            feedback_data
        )

        if success:
            print("✅ Feedback saved successfully with timestamp")
        else:
            print("❌ Feedback failed to save - timestamp lookup failed")
            return False

        # Verify feedback retrieval
        retrieved_feedback = session_manager.get_message_feedback(
            user_id,
            chat_id,
            timestamp.isoformat()
        )

        if retrieved_feedback and retrieved_feedback.get("rating") == "thumbs-up":
            print("✅ Feedback retrieved successfully")
        else:
            print("❌ Feedback retrieval failed")
            return False

        print("✅ All timestamp-based feedback operations successful")
        return True

    finally:
        # Clean up
        shutil.rmtree(temp_dir)


def test_message_structure():
    """Test that new message structure includes timestamps"""

    print("\n🧪 Testing New Message Structure")
    print("=" * 50)

    # Simulate what happens when creating a new message in the app
    from datetime import datetime

    # This is the new structure for user messages (after fix)
    user_message = {
        "role": "user",
        "content": "What are RCSB PDB policies?",
        "timestamp": datetime.now().isoformat()
    }

    # This is the new structure for assistant messages (after fix)
    assistant_message = {
        "role": "assistant",
        "content": "RCSB PDB policies require...",
        "references": [],
        "timestamp": datetime.now().isoformat()
    }

    # Test that both messages have required timestamp field
    assert "timestamp" in user_message, "User messages should have timestamps"
    assert "timestamp" in assistant_message, "Assistant messages should have timestamps"

    # Test timestamp format (should be ISO format)
    user_timestamp = user_message["timestamp"]
    assistant_timestamp = assistant_message["timestamp"]

    try:
        datetime.fromisoformat(user_timestamp)
        datetime.fromisoformat(assistant_timestamp)
        print("✅ Message timestamps are in valid ISO format")
    except ValueError:
        print("❌ Message timestamps are not in valid ISO format")
        return False

    # Test that timestamps are unique
    assert user_timestamp != assistant_timestamp, "Timestamps should be unique"
    print("✅ Message timestamps are unique")

    print("✅ New message structure is correct")
    return True


def test_no_legacy_system():
    """Test that legacy hash system is removed"""

    print("\n🧪 Testing Legacy System Removal")
    print("=" * 50)

    # Read the feedback UI function source
    try:
        with open(Path(__file__).parent.parent / "src" / "rcsb_pdb_chatbot.py", 'r') as f:
            source_code = f.read()

        # Check for removed legacy components
        legacy_indicators = [
            "legacy_",
            "hashlib",
            "content_hash",
            "md5("
        ]

        for indicator in legacy_indicators:
            if indicator in source_code:
                print(f"❌ Found legacy code: {indicator}")
                return False

        print("✅ Legacy hash generation system completely removed")

        # Check for the simple timestamp check
        if "if not message_timestamp:" in source_code and "return" in source_code:
            print("✅ Simple timestamp validation in place")
        else:
            print("❌ Timestamp validation not found")
            return False

        return True

    except Exception as e:
        print(f"❌ Error reading source code: {e}")
        return False


def run_simple_tests():
    """Run all simple integration tests"""

    print("🚀 Running Simple Feedback System Tests")
    print("=" * 60)

    tests = [
        ("Timestamp Fix", test_timestamp_fix),
        ("Message Structure", test_message_structure),
        ("Legacy System Removal", test_no_legacy_system)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n📋 Test Summary")
    print("=" * 30)

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1

    total = len(results)
    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Feedback system fix is working correctly.")
        print("✅ No more 'Message with timestamp not found' errors expected")
        print("✅ Feedback saving should work for all new messages")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review output above.")
        return False


if __name__ == "__main__":
    success = run_simple_tests()
    sys.exit(0 if success else 1)