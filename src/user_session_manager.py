#!/usr/bin/env python3
"""
User Session Manager for RAGFlow
Provides user-specific session management with multiple chats per user
"""

import json
import os
import time
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables from .env file won't be loaded.")

try:
    from .ragflow_assistant_manager import (
        RAGFlowAssistantManager, 
        create_assistant_manager, 
        create_default_assistant_config,
        StreamingResponse
    )
except ImportError:
    # For direct execution when not imported as a package
    from ragflow_assistant_manager import (
        RAGFlowAssistantManager, 
        create_assistant_manager, 
        create_default_assistant_config,
        StreamingResponse
    )


@dataclass
class ChatMessage:
    """Represents a chat message for streaming compatibility"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    message_id: Optional[str] = None
    references: Optional[List[Dict]] = None


@dataclass
class StoredMessage:
    """Represents a stored message in a chat"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    message_id: str = None  # Unique UUID for message identification
    references: Optional[List[Dict]] = None
    feedback: Optional[Dict[str, Any]] = None  # User feedback for this message


@dataclass
class UserChat:
    """Represents a single chat within a user's session"""
    chat_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    ragflow_session_id: str  # The actual RAGFlow session ID
    messages: List[StoredMessage]  # Store all messages in this chat


@dataclass
class UserSession:
    """Represents a user's session container with multiple chats"""
    user_id: str
    session_name: str
    created_at: datetime
    chats: List[UserChat]
    total_chats: int
    
    
class UserSessionManager:
    """Manages user-specific sessions and chats with RAGFlow isolation"""
    
    def __init__(self, api_key: str, base_url: str = "http://127.0.0.1:9380", data_dir: str = "user_data"):
        """
        Initialize the User Session Manager
        
        Args:
            api_key: RAGFlow API key
            base_url: RAGFlow server URL
            data_dir: Directory to store user data files
        """
        self.api_key = api_key
        self.base_url = base_url
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Create RAGFlow assistant manager
        self.assistant_manager = RAGFlowAssistantManager(api_key=api_key, base_url=base_url)
        self.assistant_config = create_default_assistant_config()
        
        # Initialize or get assistant
        try:
            self.assistant_id = self.assistant_manager.get_or_create_assistant(self.assistant_config)
            print(f"✅ Assistant ready: {self.assistant_config.name} (ID: {self.assistant_id})")
        except Exception as e:
            print(f"❌ Failed to initialize assistant: {e}")
            self.assistant_id = None
        
        # In-memory cache of user sessions
        self.user_sessions: Dict[str, UserSession] = {}
    
    def _get_user_data_file(self, user_id: str) -> Path:
        """Get the data file path for a specific user"""
        return self.data_dir / f"user_{user_id}_sessions.json"
    
    def _load_user_sessions(self, user_id: str) -> UserSession:
        """Load user sessions from file"""
        data_file = self._get_user_data_file(user_id)
        
        if not data_file.exists():
            # Create new user session
            return UserSession(
                user_id=user_id,
                session_name=f"{user_id}_main_session",
                created_at=datetime.now(),
                chats=[],
                total_chats=0
            )
        
        try:
            with open(data_file, 'r') as f:
                data = json.load(f)
            
            # Convert datetime strings back to datetime objects
            data['created_at'] = datetime.fromisoformat(data['created_at'])
            
            for chat in data['chats']:
                chat['created_at'] = datetime.fromisoformat(chat['created_at'])
                chat['updated_at'] = datetime.fromisoformat(chat['updated_at'])
                
                # Convert messages back to StoredMessage objects
                if 'messages' in chat:
                    chat_messages = []
                    for msg in chat['messages']:
                        msg['timestamp'] = datetime.fromisoformat(msg['timestamp'])
                        chat_messages.append(StoredMessage(**msg))
                    chat['messages'] = chat_messages
                else:
                    chat['messages'] = []  # For backward compatibility
            
            # Convert to UserSession object
            user_session = UserSession(
                user_id=data['user_id'],
                session_name=data['session_name'],
                created_at=data['created_at'],
                chats=[UserChat(**chat) for chat in data['chats']],
                total_chats=data['total_chats']
            )
            
            return user_session
            
        except Exception as e:
            print(f"Error loading user sessions for {user_id}: {e}")
            # Return empty session if loading fails
            return UserSession(
                user_id=user_id,
                session_name=f"{user_id}_main_session",
                created_at=datetime.now(),
                chats=[],
                total_chats=0
            )
    
    def _save_user_sessions(self, user_session: UserSession):
        """Save user sessions to file"""
        data_file = self._get_user_data_file(user_session.user_id)
        
        try:
            # Convert to dictionary for JSON serialization
            data = asdict(user_session)
            
            # Convert datetime objects to strings
            data['created_at'] = data['created_at'].isoformat()
            for chat in data['chats']:
                chat['created_at'] = chat['created_at'].isoformat()
                chat['updated_at'] = chat['updated_at'].isoformat()
                
                # Convert message timestamps to strings
                for message in chat['messages']:
                    message['timestamp'] = message['timestamp'].isoformat()
            
            with open(data_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving user sessions for {user_session.user_id}: {e}")
    
    def get_user_session(self, user_id: str) -> UserSession:
        """Get or create a user session"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = self._load_user_sessions(user_id)
        
        return self.user_sessions[user_id]
    
    def create_user_chat(self, user_id: str, chat_title: str) -> UserChat:
        """
        Create a new chat for a user (creates a new RAGFlow session)
        
        Args:
            user_id: User identifier
            chat_title: Title for the new chat
            
        Returns:
            UserChat object
        """
        try:
            # Check if assistant is available
            if not self.assistant_id:
                raise ValueError("RAGFlow assistant not available")
            
            # Create a new RAGFlow session with user-specific naming
            ragflow_session_name = f"{user_id}_{chat_title}_{int(time.time())}"
            ragflow_session_id = self.assistant_manager.create_session(self.assistant_id, ragflow_session_name)
            
            # Create user chat object
            chat_id = str(uuid.uuid4())
            user_chat = UserChat(
                chat_id=chat_id,
                title=chat_title,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                message_count=0,
                ragflow_session_id=ragflow_session_id,
                messages=[]  # Initialize with empty message list
            )
            
            # Add to user session
            user_session = self.get_user_session(user_id)
            user_session.chats.append(user_chat)
            user_session.total_chats += 1
            
            # Save to file
            self._save_user_sessions(user_session)
            
            print(f"✅ Created chat '{chat_title}' for user {user_id}")
            return user_chat
            
        except Exception as e:
            print(f"❌ Failed to create chat for user {user_id}: {e}")
            raise
    
    def list_user_chats(self, user_id: str) -> List[UserChat]:
        """List all chats for a user"""
        user_session = self.get_user_session(user_id)
        return user_session.chats
    
    def get_user_chat(self, user_id: str, chat_id: str) -> Optional[UserChat]:
        """Get a specific chat for a user"""
        user_session = self.get_user_session(user_id)
        
        for chat in user_session.chats:
            if chat.chat_id == chat_id:
                return chat
        
        return None
    
    def get_chat_messages(self, user_id: str, chat_id: str) -> List[StoredMessage]:
        """Get all messages for a specific chat"""
        user_chat = self.get_user_chat(user_id, chat_id)
        if not user_chat:
            return []
        
        return user_chat.messages
    
    def clear_chat_messages(self, user_id: str, chat_id: str) -> bool:
        """Clear all messages from a chat (keeping the chat itself)"""
        user_chat = self.get_user_chat(user_id, chat_id)
        if not user_chat:
            return False
        
        try:
            user_chat.messages = []
            user_chat.message_count = 0
            user_chat.updated_at = datetime.now()
            
            # Save updated user session
            user_session = self.get_user_session(user_id)
            self._save_user_sessions(user_session)
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to clear chat messages for {chat_id}: {e}")
            return False
    
    def send_message_to_chat(self, user_id: str, chat_id: str, message: str):
        """
        Send a message to a specific user chat
        
        Args:
            user_id: User identifier
            chat_id: Chat identifier
            message: Message content
            
        Yields:
            ChatMessage objects from RAGFlow response
        """
        # Get the user's chat
        user_chat = self.get_user_chat(user_id, chat_id)
        if not user_chat:
            raise ValueError(f"Chat {chat_id} not found for user {user_id}")
        
        try:
            # Store the user message first
            user_message = StoredMessage(
                role="user",
                content=message,
                timestamp=datetime.now(),
                message_id=str(uuid.uuid4()),
                references=None
            )
            user_chat.messages.append(user_message)
            
            # Send message to the underlying RAGFlow session and collect full response
            full_response = ""
            final_references = None

            # Generate UUID for assistant message once
            assistant_message_id = str(uuid.uuid4())
            message_timestamp = datetime.now()

            for response_chunk in self.assistant_manager.send_message(
                user_chat.ragflow_session_id,
                message,
                stream=True
            ):
                full_response = response_chunk.content
                final_references = response_chunk.references

                # Convert StreamingResponse to ChatMessage for compatibility
                chat_message = ChatMessage(
                    role="assistant",
                    content=response_chunk.content,
                    timestamp=message_timestamp,
                    message_id=assistant_message_id,
                    references=response_chunk.references
                )
                yield chat_message

            # Store the assistant's response
            if full_response:
                assistant_message = StoredMessage(
                    role="assistant",
                    content=full_response,
                    timestamp=message_timestamp,
                    message_id=assistant_message_id,
                    references=final_references
                )
                user_chat.messages.append(assistant_message)
            
            # Update chat metadata
            user_chat.updated_at = datetime.now()
            user_chat.message_count = len(user_chat.messages)
            
            # Save updated user session
            user_session = self.get_user_session(user_id)
            self._save_user_sessions(user_session)
            
        except Exception as e:
            print(f"❌ Failed to send message to chat {chat_id}: {e}")
            raise
    
    def delete_user_chat(self, user_id: str, chat_id: str) -> bool:
        """Delete a user's chat"""
        user_session = self.get_user_session(user_id)
        
        # Find and remove the chat
        for i, chat in enumerate(user_session.chats):
            if chat.chat_id == chat_id:
                try:
                    # Note: RAGFlow SDK doesn't provide direct session deletion
                    # We'll just remove from our local session management
                    
                    # Remove from user session
                    user_session.chats.pop(i)
                    user_session.total_chats -= 1
                    
                    # Save updated session
                    self._save_user_sessions(user_session)
                    
                    print(f"✅ Deleted chat '{chat.title}' for user {user_id}")
                    print(f"ℹ️  Note: RAGFlow session {chat.ragflow_session_id} remains on server")
                    return True
                    
                except Exception as e:
                    print(f"❌ Failed to delete chat {chat_id}: {e}")
                    return False
        
        print(f"⚠️ Chat {chat_id} not found for user {user_id}")
        return False
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics for a user"""
        user_session = self.get_user_session(user_id)
        
        total_messages = sum(chat.message_count for chat in user_session.chats)
        
        return {
            'user_id': user_id,
            'total_chats': user_session.total_chats,
            'total_messages': total_messages,
            'session_created': user_session.created_at.isoformat(),
            'most_recent_chat': max(
                (chat.updated_at for chat in user_session.chats), 
                default=user_session.created_at
            ).isoformat() if user_session.chats else user_session.created_at.isoformat()
        }
    
    def list_all_users(self) -> List[str]:
        """List all users with data files"""
        users = []
        for file_path in self.data_dir.glob("user_*_sessions.json"):
            # Extract user_id from filename: user_123_sessions.json -> 123
            filename = file_path.stem
            if filename.startswith("user_") and filename.endswith("_sessions"):
                user_id = filename[5:-9]  # Remove "user_" prefix and "_sessions" suffix
                users.append(user_id)
        
        return sorted(users)
    
    def cleanup_user_data(self, user_id: str) -> bool:
        """Delete all data for a user (careful!)"""
        try:
            user_session = self.get_user_session(user_id)
            
            # Note: RAGFlow SDK doesn't provide session deletion
            # Sessions remain on server but are removed from local management
            
            # Delete user data file
            data_file = self._get_user_data_file(user_id)
            if data_file.exists():
                data_file.unlink()
            
            # Remove from memory cache
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            
            print(f"✅ Cleaned up all data for user {user_id}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to cleanup data for user {user_id}: {e}")
            return False
    
    # ================= FEEDBACK MANAGEMENT METHODS =================
    
    def add_message_feedback(self, user_id: str, chat_id: str, message_id: str, feedback_data: Dict[str, Any]) -> bool:
        """
        Add feedback to a specific message

        Args:
            user_id: User identifier
            chat_id: Chat identifier
            message_id: UUID of the message
            feedback_data: Feedback dictionary with keys: rating, categories, comment, feedback_timestamp

        Returns:
            True if feedback was added successfully, False otherwise
        """
        try:
            user_chat = self.get_user_chat(user_id, chat_id)
            if not user_chat:
                print(f"❌ Chat {chat_id} not found for user {user_id}")
                return False
            
            # Find the message by UUID
            target_message = None
            for message in user_chat.messages:
                if message.message_id == message_id:
                    target_message = message
                    break

            if not target_message:
                print(f"❌ Message with ID {message_id} not found")
                return False
            
            # Add current timestamp if not provided
            if "feedback_timestamp" not in feedback_data:
                feedback_data["feedback_timestamp"] = datetime.now().isoformat()
            
            # Store feedback
            target_message.feedback = feedback_data
            
            # Update chat timestamp
            user_chat.updated_at = datetime.now()
            
            # Save updated user session
            user_session = self.get_user_session(user_id)
            self._save_user_sessions(user_session)
            
            print(f"✅ Added feedback to message {message_id}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to add feedback: {e}")
            return False
    
    def get_message_feedback(self, user_id: str, chat_id: str, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get feedback for a specific message

        Args:
            user_id: User identifier
            chat_id: Chat identifier
            message_id: UUID of the message

        Returns:
            Feedback dictionary or None if not found
        """
        try:
            user_chat = self.get_user_chat(user_id, chat_id)
            if not user_chat:
                return None
            
            # Find the message by UUID
            for message in user_chat.messages:
                if message.message_id == message_id:
                    return message.feedback
            
            return None
            
        except Exception as e:
            print(f"❌ Failed to get feedback: {e}")
            return None
    
    def update_message_feedback(self, user_id: str, chat_id: str, message_id: str, feedback_data: Dict[str, Any]) -> bool:
        """
        Update existing feedback for a message

        Args:
            user_id: User identifier
            chat_id: Chat identifier
            message_id: UUID of the message
            feedback_data: Updated feedback dictionary

        Returns:
            True if feedback was updated successfully, False otherwise
        """
        try:
            # Use the same logic as add_message_feedback
            return self.add_message_feedback(user_id, chat_id, message_id, feedback_data)
            
        except Exception as e:
            print(f"❌ Failed to update feedback: {e}")
            return False
    
    def get_chat_feedback_summary(self, user_id: str, chat_id: str) -> Dict[str, Any]:
        """
        Get a summary of all feedback for a chat
        
        Args:
            user_id: User identifier
            chat_id: Chat identifier
            
        Returns:
            Dictionary with feedback statistics
        """
        try:
            user_chat = self.get_user_chat(user_id, chat_id)
            if not user_chat:
                return {}
            
            total_messages = len([msg for msg in user_chat.messages if msg.role == "assistant"])
            feedback_count = len([msg for msg in user_chat.messages if msg.feedback is not None])
            
            positive_feedback = len([
                msg for msg in user_chat.messages 
                if msg.feedback and msg.feedback.get("rating") == "thumbs-up"
            ])
            
            negative_feedback = len([
                msg for msg in user_chat.messages 
                if msg.feedback and msg.feedback.get("rating") == "thumbs-down"
            ])
            
            # Collect all categories
            all_categories = []
            for msg in user_chat.messages:
                if msg.feedback and msg.feedback.get("categories"):
                    all_categories.extend(msg.feedback["categories"])
            
            # Count category occurrences
            category_counts = {}
            for category in all_categories:
                category_counts[category] = category_counts.get(category, 0) + 1
            
            return {
                "total_assistant_messages": total_messages,
                "messages_with_feedback": feedback_count,
                "feedback_rate": feedback_count / total_messages if total_messages > 0 else 0,
                "positive_feedback": positive_feedback,
                "negative_feedback": negative_feedback,
                "category_counts": category_counts,
                "most_common_categories": sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            }
            
        except Exception as e:
            print(f"❌ Failed to get feedback summary: {e}")
            return {}
    
    def export_chat_with_feedback(self, user_id: str, chat_id: str) -> Dict[str, Any]:
        """
        Export chat data including all feedback for analysis
        
        Args:
            user_id: User identifier
            chat_id: Chat identifier
            
        Returns:
            Dictionary with complete chat data and feedback
        """
        try:
            user_chat = self.get_user_chat(user_id, chat_id)
            if not user_chat:
                return {}
            
            # Convert chat to dictionary with feedback included
            chat_data = {
                "user_id": user_id,
                "chat_id": chat_id,
                "title": user_chat.title,
                "created_at": user_chat.created_at.isoformat(),
                "updated_at": user_chat.updated_at.isoformat(),
                "message_count": user_chat.message_count,
                "messages": []
            }
            
            for message in user_chat.messages:
                message_data = {
                    "role": message.role,
                    "content": message.content,
                    "timestamp": message.timestamp.isoformat(),
                    "references": message.references,
                    "feedback": message.feedback
                }
                chat_data["messages"].append(message_data)
            
            # Add feedback summary
            chat_data["feedback_summary"] = self.get_chat_feedback_summary(user_id, chat_id)
            
            return chat_data
            
        except Exception as e:
            print(f"❌ Failed to export chat with feedback: {e}")
            return {}


def create_manager() -> UserSessionManager:
    """Create a UserSessionManager with environment-based configuration"""
    # Load configuration from environment variables with fallback defaults
    API_KEY = os.getenv("RAGFLOW_API_KEY")
    BASE_URL = os.getenv("RAGFLOW_BASE_URL", "http://127.0.0.1:9380")
    DATA_DIR = os.getenv("USER_DATA_DIR", "user_data")
    
    if not API_KEY or API_KEY == "your-ragflow-api-key-here":
        raise ValueError("RAGFLOW_API_KEY environment variable must be set with a valid API key")
    
    return UserSessionManager(api_key=API_KEY, base_url=BASE_URL, data_dir=DATA_DIR)


# Example usage and testing
if __name__ == "__main__":
    print("🚀 Testing User Session Manager...")
    
    # Create manager
    manager = create_manager()
    
    # Test with multiple users
    users = ["alice", "bob", "charlie"]
    
    for user in users:
        print(f"\n👤 Testing user: {user}")
        
        # Create some chats for each user
        chat1 = manager.create_user_chat(user, "Protein Research")
        chat2 = manager.create_user_chat(user, "Data Analysis")
        
        # List user's chats
        user_chats = manager.list_user_chats(user)
        print(f"   User {user} has {len(user_chats)} chats")
        
        # Send a test message
        test_message = f"Hello from {user}! What is RCSB PDB?"
        print(f"   Sending message to first chat...")
        
        response_text = ""
        for response in manager.send_message_to_chat(user, chat1.chat_id, test_message):
            response_text = response.content
            if len(response_text) > 50:  # Stop after getting some response
                break
        
        print(f"   Response received: {len(response_text)} characters")
        
        # Get user stats
        stats = manager.get_user_stats(user)
        print(f"   Stats: {stats['total_chats']} chats, {stats['total_messages']} messages")
    
    # List all users
    all_users = manager.list_all_users()
    print(f"\n📊 Total users with data: {all_users}")
    
    print("\n✅ User Session Manager test completed!")