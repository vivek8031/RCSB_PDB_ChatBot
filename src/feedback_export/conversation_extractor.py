"""
Conversation Extractor

Reads user session JSON files and extracts question-answer pairs with feedback.
"""

import json
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from .config import QAPair


class ConversationExtractor:
    """Extract Q&A pairs from user session JSON files"""

    def __init__(self, user_data_dir: Path):
        """
        Initialize extractor

        Args:
            user_data_dir: Directory containing user session JSON files
        """
        self.user_data_dir = user_data_dir
        self.logger = logging.getLogger("feedback_export.conversation_extractor")

    def get_all_qa_pairs(self) -> List[QAPair]:
        """
        Extract all Q&A pairs from all user session files

        Returns:
            List of QAPair objects
        """
        all_pairs = []

        # Find all user session JSON files
        json_files = list(self.user_data_dir.glob("user_*_sessions.json"))

        self.logger.info(f"Found {len(json_files)} user session files")

        for json_file in json_files:
            try:
                pairs = self._extract_from_file(json_file)
                all_pairs.extend(pairs)
                self.logger.info(f"✓ Extracted {len(pairs)} Q&A pairs from {json_file.name}")
            except Exception as e:
                self.logger.error(f"✗ Failed to extract from {json_file.name}: {e}")

        self.logger.info(f"Total Q&A pairs extracted: {len(all_pairs)}")
        return all_pairs

    def _extract_from_file(self, json_file: Path) -> List[QAPair]:
        """
        Extract Q&A pairs from a single user session file

        Args:
            json_file: Path to user session JSON file

        Returns:
            List of QAPair objects
        """
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        user_id = data.get("user_id", "unknown")
        chats = data.get("chats", [])

        pairs = []

        for chat in chats:
            chat_title = chat.get("title", "Untitled Chat")
            messages = chat.get("messages", [])

            # Extract Q&A pairs from messages
            chat_pairs = self._extract_qa_pairs(messages, user_id, chat_title)
            pairs.extend(chat_pairs)

        return pairs

    def _extract_qa_pairs(
        self,
        messages: List[Dict[str, Any]],
        user_id: str,
        chat_title: str
    ) -> List[QAPair]:
        """
        Extract Q&A pairs from a conversation message list

        Messages alternate: user -> assistant -> user -> assistant
        Each user message is paired with the following assistant message.

        Args:
            messages: List of message dictionaries
            user_id: User ID
            chat_title: Title of the chat

        Returns:
            List of QAPair objects
        """
        pairs = []
        i = 0

        while i < len(messages):
            # Look for user message
            if messages[i].get("role") == "user":
                user_msg = messages[i]

                # Check if there's a following assistant message
                if i + 1 < len(messages) and messages[i + 1].get("role") == "assistant":
                    assistant_msg = messages[i + 1]

                    # Create Q&A pair
                    qa_pair = self._create_qa_pair(user_msg, assistant_msg, user_id, chat_title)
                    if qa_pair:
                        pairs.append(qa_pair)

                    # Move to next user message (skip the assistant message we just processed)
                    i += 2
                else:
                    # User message without response (skip)
                    i += 1
            else:
                # Not a user message (skip)
                i += 1

        return pairs

    def _create_qa_pair(
        self,
        user_msg: Dict[str, Any],
        assistant_msg: Dict[str, Any],
        user_id: str,
        chat_title: str
    ) -> Optional[QAPair]:
        """
        Create a QAPair object from user and assistant messages

        Args:
            user_msg: User message dictionary
            assistant_msg: Assistant message dictionary
            user_id: User ID
            chat_title: Chat title

        Returns:
            QAPair object or None if invalid
        """
        try:
            # Extract basic data
            user_question = user_msg.get("content", "")
            ai_response = assistant_msg.get("content", "")
            question_timestamp = user_msg.get("timestamp", "")
            answer_timestamp = assistant_msg.get("timestamp", "")
            message_id = assistant_msg.get("message_id", "")

            # Skip if missing essential data
            if not user_question or not ai_response or not message_id:
                self.logger.warning("Skipping Q&A pair with missing essential data")
                return None

            # Extract feedback (if present)
            feedback = assistant_msg.get("feedback")
            feedback_rating = None
            feedback_categories = []
            feedback_comment = None
            feedback_timestamp = None

            if feedback and isinstance(feedback, dict):
                feedback_rating = feedback.get("rating")
                feedback_categories = feedback.get("categories", [])
                feedback_comment = feedback.get("comment")
                feedback_timestamp = feedback.get("feedback_timestamp")

            # Extract referenced documents
            referenced_documents = []
            references = assistant_msg.get("references")
            if references and isinstance(references, list):
                for ref in references:
                    if isinstance(ref, dict):
                        doc_name = ref.get("document_name")
                        if doc_name:
                            referenced_documents.append(doc_name)

            # Remove duplicates from referenced documents
            referenced_documents = list(set(referenced_documents))

            # Generate unique export ID
            export_id = str(uuid.uuid4())

            return QAPair(
                export_id=export_id,
                message_id=message_id,
                user_id=user_id,
                chat_title=chat_title,
                question_timestamp=question_timestamp,
                user_question=user_question,
                answer_timestamp=answer_timestamp,
                ai_response=ai_response,
                feedback_rating=feedback_rating,
                feedback_categories=feedback_categories,
                feedback_comment=feedback_comment,
                feedback_timestamp=feedback_timestamp,
                referenced_documents=referenced_documents
            )

        except Exception as e:
            self.logger.error(f"Failed to create Q&A pair: {e}")
            return None
