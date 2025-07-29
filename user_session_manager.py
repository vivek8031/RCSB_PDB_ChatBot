#!/usr/bin/env python3
"""
User Session Manager for RAGFlow
Provides user-specific session management with multiple chats per user
"""

import json
import time
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path

from ragflow_simple_client import RAGFlowSimpleClient, ChatSession, ChatMessage


@dataclass
class StoredMessage:
    """Represents a stored message in a chat"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    references: Optional[List[Dict]] = None


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
        
        # Create RAGFlow client
        self.ragflow_client = RAGFlowSimpleClient(api_key=api_key, base_url=base_url)
        
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
            # Create a new RAGFlow session with user-specific naming
            ragflow_session_name = f"{user_id}_{chat_title}_{int(time.time())}"
            ragflow_session = self.ragflow_client.create_session(ragflow_session_name)
            
            # Create user chat object
            chat_id = str(uuid.uuid4())
            user_chat = UserChat(
                chat_id=chat_id,
                title=chat_title,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                message_count=0,
                ragflow_session_id=ragflow_session.session_id,
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
                references=None
            )
            user_chat.messages.append(user_message)
            
            # Send message to the underlying RAGFlow session and collect full response
            full_response = ""
            final_references = None
            
            for response_chunk in self.ragflow_client.send_message(
                user_chat.ragflow_session_id, 
                message, 
                stream=True
            ):
                full_response = response_chunk.content
                final_references = response_chunk.references
                yield response_chunk
            
            # Store the assistant's response
            if full_response:
                assistant_message = StoredMessage(
                    role="assistant",
                    content=full_response,
                    timestamp=datetime.now(),
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
                    # Delete the underlying RAGFlow session
                    self.ragflow_client.delete_session(chat.ragflow_session_id)
                    
                    # Remove from user session
                    user_session.chats.pop(i)
                    user_session.total_chats -= 1
                    
                    # Save updated session
                    self._save_user_sessions(user_session)
                    
                    print(f"✅ Deleted chat '{chat.title}' for user {user_id}")
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
            
            # Delete all RAGFlow sessions for this user
            for chat in user_session.chats:
                self.ragflow_client.delete_session(chat.ragflow_session_id)
            
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


def create_manager() -> UserSessionManager:
    """Create a UserSessionManager with default settings"""
    API_KEY = "ragflow-VjNjM4Zjk0NmMyZDExZjA4MjQyNTY3YT"
    BASE_URL = "http://127.0.0.1:9380"
    
    return UserSessionManager(api_key=API_KEY, base_url=BASE_URL)


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