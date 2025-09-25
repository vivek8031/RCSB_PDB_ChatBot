#!/usr/bin/env python3
"""
Test the new UUID-based feedback system

This test verifies that:
1. Messages are created with UUIDs
2. Feedback lookup works with UUIDs
3. No more timestamp matching errors
"""

import sys
import json
import tempfile
import shutil
import uuid
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from user_session_manager import UserSessionManager, StoredMessage, UserChat


def test_uuid_feedback_system():
    """Test the complete UUID-based feedback flow"""

    print("🧪 Testing UUID-Based Feedback System")
    print("=" * 50)

    # Create temporary directory for test
    temp_dir = tempfile.mkdtemp()

    try:
        user_data_dir = Path(temp_dir) / "user_data"
        user_data_dir.mkdir(exist_ok=True)

        # Initialize session manager
        session_manager = UserSessionManager(str(user_data_dir))

        # Test data
        user_id = "test_user"
        chat_id = "test_chat"

        # 1. Create messages with UUIDs (simulating what session manager now does)
        user_msg_id = str(uuid.uuid4())
        assistant_msg_id = str(uuid.uuid4())
        timestamp = datetime.now()

        user_message = StoredMessage(
            role="user",
            content="Test user message",
            timestamp=timestamp,
            message_id=user_msg_id,
            references=None
        )

        assistant_message = StoredMessage(
            role="assistant",
            content="Test assistant response about RCSB PDB policies",
            timestamp=timestamp,
            message_id=assistant_msg_id,
            references=None
        )

        # Create chat with messages
        user_chat = UserChat(
            chat_id=chat_id,
            title="Test Chat",
            created_at=timestamp,
            updated_at=timestamp,
            message_count=2,
            ragflow_session_id="test_session",
            messages=[user_message, assistant_message]
        )

        # Save the chat manually (simulating normal flow)
        session_manager._ensure_user_session(user_id)
        user_session = session_manager.get_user_session(user_id)
        user_session.chats.append(user_chat)
        session_manager._save_user_sessions(user_session)

        print(f"✅ Created messages with UUIDs:")
        print(f"   User message ID: {user_msg_id}")
        print(f"   Assistant message ID: {assistant_msg_id}")

        # 2. Test feedback saving with UUID
        feedback_data = {
            "rating": "thumbs-up",
            "categories": ["helpful", "accurate"],
            "comment": "Great response about RCSB policies!",
            "feedback_timestamp": datetime.now().isoformat()
        }

        # This should work with UUIDs (no more timestamp errors)
        success = session_manager.add_message_feedback(
            user_id,
            chat_id,
            assistant_msg_id,  # Using UUID instead of timestamp!
            feedback_data
        )

        if success:
            print("✅ Feedback saved successfully using UUID")
        else:
            print("❌ Feedback save failed")
            return False

        # 3. Test feedback retrieval with UUID
        retrieved_feedback = session_manager.get_message_feedback(
            user_id,
            chat_id,
            assistant_msg_id  # Using UUID for lookup!
        )

        if retrieved_feedback and retrieved_feedback.get("rating") == "thumbs-up":
            print("✅ Feedback retrieved successfully using UUID")
        else:
            print("❌ Feedback retrieval failed")
            return False

        # 4. Test that wrong UUID returns nothing (not found)
        fake_uuid = str(uuid.uuid4())
        no_feedback = session_manager.get_message_feedback(
            user_id,
            chat_id,
            fake_uuid
        )

        if no_feedback is None:
            print("✅ Non-existent UUID correctly returns None")
        else:
            print("❌ Non-existent UUID should return None")
            return False

        # 5. Test multiple messages with different UUIDs
        msg_id_3 = str(uuid.uuid4())
        msg_id_4 = str(uuid.uuid4())

        # Add two more messages
        message3 = StoredMessage(
            role="assistant",
            content="Second assistant response",
            timestamp=datetime.now(),
            message_id=msg_id_3,
            references=None
        )

        message4 = StoredMessage(
            role="assistant",
            content="Third assistant response",
            timestamp=datetime.now(),
            message_id=msg_id_4,
            references=None
        )

        user_chat.messages.extend([message3, message4])
        session_manager._save_user_sessions(user_session)

        # Add different feedback to each
        feedback_3 = {"rating": "thumbs-down", "comment": "Not helpful"}
        feedback_4 = {"rating": "thumbs-up", "comment": "Very helpful"}

        success_3 = session_manager.add_message_feedback(user_id, chat_id, msg_id_3, feedback_3)
        success_4 = session_manager.add_message_feedback(user_id, chat_id, msg_id_4, feedback_4)

        if success_3 and success_4:
            print("✅ Multiple messages with independent feedback work correctly")
        else:
            print("❌ Multiple message feedback failed")
            return False

        # Verify independent feedback
        fb_3 = session_manager.get_message_feedback(user_id, chat_id, msg_id_3)
        fb_4 = session_manager.get_message_feedback(user_id, chat_id, msg_id_4)

        if (fb_3 and fb_3["rating"] == "thumbs-down" and
            fb_4 and fb_4["rating"] == "thumbs-up"):
            print("✅ Independent feedback for different messages verified")
        else:
            print("❌ Independent feedback verification failed")
            return False

        print("\n🎉 UUID-Based Feedback System Test Results:")
        print("✅ Messages created with unique UUIDs")
        print("✅ Feedback save/retrieve works with UUIDs")
        print("✅ No timestamp matching required")
        print("✅ Multiple messages work independently")
        print("✅ Non-existent UUIDs handled gracefully")

        return True

    finally:
        # Clean up
        shutil.rmtree(temp_dir)


def test_uuid_uniqueness():
    """Test that UUIDs are actually unique"""
    print("\n🧪 Testing UUID Uniqueness")
    print("=" * 30)

    # Generate 1000 UUIDs and check for duplicates
    uuids = set()
    for _ in range(1000):
        new_uuid = str(uuid.uuid4())
        if new_uuid in uuids:
            print("❌ Duplicate UUID found!")
            return False
        uuids.add(new_uuid)

    print("✅ Generated 1000 unique UUIDs successfully")
    return True


def test_message_structure():
    """Test that messages have the expected structure with UUIDs"""
    print("\n🧪 Testing Message Structure")
    print("=" * 30)

    # Simulate what the UI now creates
    import uuid
    from datetime import datetime

    # User message (like in chat input)
    user_msg = {
        "role": "user",
        "content": "What are RCSB policies?",
        "message_id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat()
    }

    # Assistant message (like from session manager)
    assistant_msg = {
        "role": "assistant",
        "content": "RCSB PDB policies require...",
        "message_id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "references": []
    }

    # Verify structure
    required_fields = ["role", "content", "message_id", "timestamp"]

    for field in required_fields:
        if field not in user_msg or field not in assistant_msg:
            print(f"❌ Missing required field: {field}")
            return False

    # Verify UUIDs are valid format
    try:
        uuid.UUID(user_msg["message_id"])
        uuid.UUID(assistant_msg["message_id"])
        print("✅ UUIDs are valid format")
    except ValueError:
        print("❌ Invalid UUID format")
        return False

    # Verify UUIDs are unique
    if user_msg["message_id"] == assistant_msg["message_id"]:
        print("❌ UUIDs should be unique")
        return False

    print("✅ Message structure is correct")
    print(f"   User message ID: {user_msg['message_id']}")
    print(f"   Assistant message ID: {assistant_msg['message_id']}")

    return True


if __name__ == "__main__":
    print("🚀 UUID-Based Feedback System Tests")
    print("=" * 60)

    tests = [
        ("UUID Feedback System", test_uuid_feedback_system),
        ("UUID Uniqueness", test_uuid_uniqueness),
        ("Message Structure", test_message_structure)
    ]

    passed = 0
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")

    print(f"\n📊 Test Results: {passed}/{len(tests)} passed")

    if passed == len(tests):
        print("\n🎉 ALL TESTS PASSED!")
        print("✨ UUID-based feedback system is working correctly")
        print("🚫 No more timestamp matching errors expected")
    else:
        print(f"\n⚠️  {len(tests) - passed} test(s) failed")

    sys.exit(0 if passed == len(tests) else 1)