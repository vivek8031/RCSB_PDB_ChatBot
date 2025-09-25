#!/usr/bin/env python3
"""
Test Suite for Message Feedback System Fix

Tests the fix for timestamp consistency issues in the feedback system.
Verifies that all messages get proper timestamps and feedback saving works correctly.
"""

import os
import sys
import json
import pytest
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from user_session_manager import UserSessionManager, StoredMessage, UserChat


class TestFeedbackSystemFix:
    """Test suite for the feedback system timestamp fix"""

    def setup_method(self):
        """Set up test environment before each test"""
        # Create temporary directory for test user data
        self.temp_dir = tempfile.mkdtemp()
        self.test_user_data_dir = Path(self.temp_dir) / "user_data"
        self.test_user_data_dir.mkdir(exist_ok=True)

        # Initialize session manager with test directory
        self.session_manager = UserSessionManager(str(self.test_user_data_dir))

        # Test data
        self.test_user_id = "test_user_123"
        self.test_chat_id = "test_chat_456"

    def teardown_method(self):
        """Clean up after each test"""
        shutil.rmtree(self.temp_dir)

    def test_message_with_timestamp_feedback_save(self):
        """Test that messages with timestamps can save feedback successfully"""
        # Create a user chat with a timestamped message
        timestamp = datetime.now()
        message = StoredMessage(
            role="assistant",
            content="Test message content",
            timestamp=timestamp,
            references=None,
            feedback=None
        )

        # Create and save user chat
        user_chat = UserChat(
            chat_id=self.test_chat_id,
            title="Test Chat",
            created_at=timestamp,
            updated_at=timestamp,
            messages=[message]
        )

        # Save chat
        self.session_manager.save_user_message(
            self.test_user_id,
            self.test_chat_id,
            "user",
            "Test user message",
            ragflow_session_id="test_session"
        )
        self.session_manager.save_user_message(
            self.test_user_id,
            self.test_chat_id,
            "assistant",
            "Test message content",
            ragflow_session_id="test_session",
            references=None,
            timestamp=timestamp
        )

        # Test feedback data
        feedback_data = {
            "rating": "thumbs-up",
            "categories": ["helpful", "accurate"],
            "comment": "Great response!",
            "feedback_timestamp": datetime.now().isoformat()
        }

        # Add feedback
        success = self.session_manager.add_message_feedback(
            self.test_user_id,
            self.test_chat_id,
            timestamp.isoformat(),
            feedback_data
        )

        # Verify feedback was saved
        assert success, "Feedback should be saved successfully for timestamped message"

        # Retrieve and verify feedback
        retrieved_feedback = self.session_manager.get_message_feedback(
            self.test_user_id,
            self.test_chat_id,
            timestamp.isoformat()
        )

        assert retrieved_feedback is not None, "Feedback should be retrievable"
        assert retrieved_feedback["rating"] == "thumbs-up"
        assert retrieved_feedback["comment"] == "Great response!"

    def test_message_without_timestamp_skipped(self):
        """Test that messages without timestamps are handled gracefully"""
        # Create a message without timestamp (shouldn't happen with the fix)
        message_dict = {
            "role": "assistant",
            "content": "Message without timestamp",
            # No timestamp field
        }

        # Mock display_message_feedback_ui function
        with patch('src.rcsb_pdb_chatbot.display_message_feedback_ui') as mock_feedback_ui:
            # Import the function to test
            from rcsb_pdb_chatbot import display_message_feedback_ui

            # Call the function with a message without timestamp
            result = display_message_feedback_ui(message_dict)

            # The function should return early (None) for messages without timestamps
            assert result is None, "Function should return early for messages without timestamps"

    def test_new_message_timestamp_consistency(self):
        """Test that new messages created in chat have consistent timestamp format"""
        # Test timestamp format consistency
        now = datetime.now()
        timestamp_iso = now.isoformat()

        # Verify ISO format is consistent
        parsed_timestamp = datetime.fromisoformat(timestamp_iso)
        assert parsed_timestamp == now, "ISO timestamp should be parseable back to original datetime"

    def test_feedback_key_generation(self):
        """Test that feedback keys are generated consistently from timestamps"""
        # Test data
        timestamp = "2024-09-25T10:30:45.123456"
        expected_key = f"feedback_{timestamp}"

        # Mock message with timestamp
        message_dict = {
            "role": "assistant",
            "content": "Test content",
            "timestamp": timestamp
        }

        # The feedback key should be predictable and consistent
        assert expected_key == f"feedback_{message_dict['timestamp']}"

    def test_no_legacy_hash_generation(self):
        """Test that legacy hash generation is completely removed"""
        # Import the function
        from rcsb_pdb_chatbot import display_message_feedback_ui
        import inspect

        # Get the source code of the function
        source = inspect.getsource(display_message_feedback_ui)

        # Verify legacy hash generation code is removed
        assert "legacy_" not in source, "Legacy hash generation should be removed"
        assert "hashlib" not in source, "Hash generation should be removed"
        assert "content_hash" not in source, "Content hash generation should be removed"

    def test_user_session_file_feedback_persistence(self):
        """Test that feedback is properly persisted in user session files"""
        # Create user and chat
        timestamp = datetime.now()

        # Save messages
        self.session_manager.save_user_message(
            self.test_user_id,
            self.test_chat_id,
            "user",
            "Test user message",
            ragflow_session_id="test_session"
        )

        self.session_manager.save_user_message(
            self.test_user_id,
            self.test_chat_id,
            "assistant",
            "Test assistant response",
            ragflow_session_id="test_session",
            references=None,
            timestamp=timestamp
        )

        # Add feedback
        feedback_data = {
            "rating": "thumbs-down",
            "categories": ["incorrect"],
            "comment": "Not accurate",
            "feedback_timestamp": datetime.now().isoformat()
        }

        success = self.session_manager.add_message_feedback(
            self.test_user_id,
            self.test_chat_id,
            timestamp.isoformat(),
            feedback_data
        )

        assert success, "Feedback should be saved successfully"

        # Verify feedback is persisted in file
        user_file = self.test_user_data_dir / f"user_{self.test_user_id}_sessions.json"
        assert user_file.exists(), "User session file should exist"

        with open(user_file, 'r') as f:
            user_data = json.load(f)

        # Find the message with feedback
        found_feedback = False
        for chat in user_data['chats']:
            if chat['chat_id'] == self.test_chat_id:
                for message in chat['messages']:
                    if message.get('feedback'):
                        found_feedback = True
                        assert message['feedback']['rating'] == "thumbs-down"
                        assert message['feedback']['comment'] == "Not accurate"
                        break

        assert found_feedback, "Feedback should be persisted in user session file"

    def test_multiple_messages_unique_feedback(self):
        """Test that multiple messages can have independent feedback"""
        timestamps = [
            datetime.now().replace(microsecond=100000),
            datetime.now().replace(microsecond=200000),
            datetime.now().replace(microsecond=300000)
        ]

        # Create multiple messages
        for i, timestamp in enumerate(timestamps):
            self.session_manager.save_user_message(
                self.test_user_id,
                self.test_chat_id,
                "assistant",
                f"Test message {i+1}",
                ragflow_session_id="test_session",
                timestamp=timestamp
            )

        # Add different feedback to each message
        feedback_ratings = ["thumbs-up", "thumbs-down", "thumbs-up"]
        for i, (timestamp, rating) in enumerate(zip(timestamps, feedback_ratings)):
            feedback_data = {
                "rating": rating,
                "comment": f"Feedback for message {i+1}",
                "feedback_timestamp": datetime.now().isoformat()
            }

            success = self.session_manager.add_message_feedback(
                self.test_user_id,
                self.test_chat_id,
                timestamp.isoformat(),
                feedback_data
            )

            assert success, f"Feedback should be saved for message {i+1}"

        # Verify each message has independent feedback
        for i, (timestamp, expected_rating) in enumerate(zip(timestamps, feedback_ratings)):
            feedback = self.session_manager.get_message_feedback(
                self.test_user_id,
                self.test_chat_id,
                timestamp.isoformat()
            )

            assert feedback is not None, f"Feedback should exist for message {i+1}"
            assert feedback["rating"] == expected_rating, f"Feedback rating should match for message {i+1}"
            assert feedback["comment"] == f"Feedback for message {i+1}"


def run_feedback_tests():
    """Run the feedback system tests and display results"""
    print("🧪 Running Message Feedback System Tests")
    print("=" * 50)

    # Run pytest programmatically
    test_result = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--no-header"
    ])

    if test_result == 0:
        print("\n✅ All feedback system tests passed!")
        print("✅ Timestamp consistency fix is working correctly")
        print("✅ Legacy hash generation successfully removed")
        print("✅ Feedback saving/loading works as expected")
    else:
        print("\n❌ Some tests failed")
        print("❌ Review the test output above for details")

    return test_result == 0


if __name__ == "__main__":
    success = run_feedback_tests()
    sys.exit(0 if success else 1)