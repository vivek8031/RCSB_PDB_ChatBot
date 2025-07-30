"""
Simplified RAGFlow Client
A clean wrapper around the RAGFlow SDK for the 'RCSB ChatBot v2' assistant
"""

import os
import time
from typing import Dict, List, Optional, Any, Generator, Tuple
from dataclasses import dataclass
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
except ImportError:
    pass  # python-dotenv not installed, environment variables from .env file won't be loaded

try:
    from ragflow_sdk import RAGFlow
except ImportError:
    raise ImportError("RAGFlow SDK not installed. Run: pip install ragflow-sdk")

try:
    from openai import OpenAI
except ImportError:
    print("Warning: OpenAI library not installed. OpenAI-compatible API will not be available.")
    OpenAI = None


@dataclass
class ChatMessage:
    """Represents a chat message"""
    content: str
    role: str  # 'user' or 'assistant'
    timestamp: datetime
    message_id: Optional[str] = None
    references: Optional[List[Dict]] = None


@dataclass
class ChatSession:
    """Represents a chat session"""
    session_id: str
    name: str
    chat_id: str
    created_at: datetime
    messages: List[ChatMessage]


class RAGFlowSimpleClient:
    """Simplified client for RAGFlow 'RCSB ChatBot v2' assistant"""
    
    def __init__(self, api_key: str, base_url: str = "http://127.0.0.1:9380"):
        """
        Initialize the RAGFlow client
        
        Args:
            api_key: RAGFlow API key
            base_url: RAGFlow server URL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.assistant_name = os.getenv("RAGFLOW_ASSISTANT_NAME", "RCSB ChatBot v2")
        
        # Initialize clients
        try:
            self.rag_client = RAGFlow(api_key=api_key, base_url=base_url)
            self.assistant = None
            self._find_assistant()
            
            # Initialize OpenAI client for alternative API access
            if OpenAI:
                self.openai_client = None  # Will be initialized per-session
            else:
                self.openai_client = None
                
        except Exception as e:
            raise ConnectionError(f"Failed to initialize RAGFlow client: {e}")
    
    def _find_assistant(self):
        """Find the RCSB ChatBot v2 assistant"""
        try:
            assistants = self.rag_client.list_chats()
            
            for assistant in assistants:
                if assistant.name == self.assistant_name:
                    self.assistant = assistant
                    return
            
            # If not found, list available assistants
            available = [a.name for a in assistants]
            raise ValueError(f"Assistant '{self.assistant_name}' not found. Available: {available}")
            
        except Exception as e:
            raise ConnectionError(f"Failed to find assistant: {e}")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to RAGFlow"""
        try:
            assistants = self.rag_client.list_chats()
            return {
                'success': True,
                'assistant_found': self.assistant is not None,
                'assistant_id': self.assistant.id if self.assistant else None,
                'total_assistants': len(assistants)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_session(self, name: Optional[str] = None) -> ChatSession:
        """
        Create a new chat session
        
        Args:
            name: Optional session name
            
        Returns:
            ChatSession object
        """
        if not self.assistant:
            raise ValueError("Assistant not found")
        
        try:
            if not name:
                name = f"Chat Session {int(time.time())}"
            
            session = self.assistant.create_session(name=name)
            
            # Create initial message if available
            messages = []
            if hasattr(session, 'message') and session.message:
                for msg in session.message:
                    messages.append(ChatMessage(
                        content=msg.get('content', ''),
                        role=msg.get('role', 'assistant'),
                        timestamp=datetime.now()
                    ))
            
            return ChatSession(
                session_id=session.id,
                name=session.name,
                chat_id=getattr(session, 'chat_id', self.assistant.id),
                created_at=datetime.now(),
                messages=messages
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to create session: {e}")
    
    def list_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List existing sessions
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of session info dictionaries
        """
        if not self.assistant:
            raise ValueError("Assistant not found")
        
        try:
            sessions = self.assistant.list_sessions(page_size=limit)
            
            session_list = []
            for session in sessions:
                session_list.append({
                    'id': session.id,
                    'name': session.name,
                    'chat_id': getattr(session, 'chat_id', self.assistant.id)
                })
            
            return session_list
            
        except Exception as e:
            raise RuntimeError(f"Failed to list sessions: {e}")
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session
        
        Args:
            session_id: ID of session to delete
            
        Returns:
            True if successful
        """
        if not self.assistant:
            raise ValueError("Assistant not found")
        
        try:
            self.assistant.delete_sessions(ids=[session_id])
            return True
        except Exception as e:
            print(f"Warning: Failed to delete session {session_id}: {e}")
            return False
    
    def send_message(self, session_id: str, message: str, stream: bool = True, use_openai_api: bool = True, **kwargs) -> Generator[ChatMessage, None, None]:
        """
        Send a message and get response
        
        Args:
            session_id: Session ID to send message to
            message: User message content
            stream: Whether to stream the response
            use_openai_api: Whether to use OpenAI-compatible API (recommended for references)
            **kwargs: Additional parameters passed to session.ask()
            
        Yields:
            ChatMessage objects for the response
        """
        if not self.assistant:
            raise ValueError("Assistant not found")
        
        # Try OpenAI API first if available and requested
        if use_openai_api and OpenAI:
            try:
                for response in self.send_message_openai_api(session_id, message, stream):
                    yield response
                return
            except Exception as e:
                print(f"Warning: OpenAI API failed, falling back to SDK: {e}")
                # Fall through to SDK method
        
        try:
            # Fallback: Use the SDK method
            # Get the session object - we need to recreate it
            sessions = self.assistant.list_sessions()
            target_session = None
            
            for session in sessions:
                if session.id == session_id:
                    target_session = session
                    break
            
            if not target_session:
                raise ValueError(f"Session {session_id} not found")
            
            # Send message and handle response with all parameters
            # Try multiple parameter combinations to ensure references work
            ask_params = {
                'question': message,
                'stream': stream,
                'reference': True,
                'show_quote': True,
                **kwargs  # Include any additional parameters
            }
            
            response_generator = target_session.ask(**ask_params)
            
            if stream:
                # Handle streaming response
                full_content = ""
                for chunk in response_generator:
                    new_content = chunk.content[len(full_content):]
                    if new_content:
                        full_content = chunk.content
                        
                        # Create message object
                        chat_msg = ChatMessage(
                            content=chunk.content,
                            role='assistant',
                            timestamp=datetime.now(),
                            message_id=getattr(chunk, 'id', None),
                            references=getattr(chunk, 'reference', None)
                        )
                        
                        yield chat_msg
            else:
                # Handle non-streaming response (but it still returns a generator)
                final_response = None
                for response in response_generator:
                    final_response = response
                
                if final_response:
                    chat_msg = ChatMessage(
                        content=final_response.content,
                        role='assistant',
                        timestamp=datetime.now(),
                        message_id=getattr(final_response, 'id', None),
                        references=getattr(final_response, 'reference', None)
                    )
                    yield chat_msg
                    
        except Exception as e:
            # Return error message
            error_msg = ChatMessage(
                content=f"Error: {str(e)}",
                role='assistant',
                timestamp=datetime.now()
            )
            yield error_msg
    
    def send_message_openai_api(self, session_id: str, message: str, stream: bool = True) -> Generator[ChatMessage, None, None]:
        """
        Send a message using OpenAI-compatible API with references enabled
        
        Args:
            session_id: Session ID to send message to
            message: User message content
            stream: Whether to stream the response
            
        Yields:
            ChatMessage objects for the response
        """
        if not self.assistant:
            raise ValueError("Assistant not found")
        
        if not OpenAI:
            raise ImportError("OpenAI library not installed. Cannot use OpenAI-compatible API.")
        
        try:
            # Create OpenAI client for this session
            openai_client = OpenAI(
                api_key=self.api_key,
                base_url=f"{self.base_url}/api/v1/chats_openai/{self.assistant.id}"
            )
            
            # Create chat completion with references enabled
            completion = openai_client.chat.completions.create(
                model="ragflow-model",  # Can be any value according to docs
                messages=[
                    {"role": "user", "content": message}
                ],
                stream=stream,
                extra_body={"reference": True}
            )
            
            if stream:
                # Handle streaming response
                full_content = ""
                references = []
                
                for chunk in completion:
                    if chunk.choices and len(chunk.choices) > 0:
                        choice = chunk.choices[0]
                        
                        # Get content delta
                        if hasattr(choice, 'delta') and hasattr(choice.delta, 'content') and choice.delta.content:
                            full_content += choice.delta.content
                        
                        # Check for references when streaming finishes
                        if choice.finish_reason == "stop":
                            if hasattr(choice.delta, 'reference'):
                                references = choice.delta.reference
                            
                            # Get final content if available
                            if hasattr(choice.delta, 'final_content'):
                                full_content = choice.delta.final_content
                        
                        # Yield the current state
                        chat_msg = ChatMessage(
                            content=full_content,
                            role='assistant',
                            timestamp=datetime.now(),
                            message_id=getattr(chunk, 'id', None),
                            references=references if references else None
                        )
                        yield chat_msg
            else:
                # Handle non-streaming response
                if completion.choices and len(completion.choices) > 0:
                    choice = completion.choices[0]
                    content = choice.message.content
                    references = getattr(choice.message, 'reference', None)
                    
                    chat_msg = ChatMessage(
                        content=content,
                        role='assistant',
                        timestamp=datetime.now(),
                        message_id=getattr(completion, 'id', None),
                        references=references
                    )
                    yield chat_msg
                    
        except Exception as e:
            # Return error message
            error_msg = ChatMessage(
                content=f"OpenAI API Error: {str(e)}",
                role='assistant',
                timestamp=datetime.now()
            )
            yield error_msg
    
    def get_assistant_info(self) -> Dict[str, Any]:
        """Get information about the assistant"""
        if not self.assistant:
            return {'error': 'Assistant not found'}
        
        return {
            'name': self.assistant.name,
            'id': self.assistant.id,
            'dataset_ids': getattr(self.assistant, 'dataset_ids', []),
            'description': getattr(self.assistant, 'description', 'RCSB PDB ChatBot Assistant')
        }


# Utility functions for the Streamlit app
def format_message_content(content: str, max_length: int = 100) -> str:
    """Format message content for display"""
    if len(content) <= max_length:
        return content
    return content[:max_length] + "..."


def extract_references(message: ChatMessage) -> List[Dict[str, Any]]:
    """Extract and format references from a message"""
    if not message.references:
        return []
    
    formatted_refs = []
    for ref in message.references:
        if isinstance(ref, dict):
            formatted_refs.append({
                'document_name': ref.get('document_name', 'Unknown'),
                'content': ref.get('content', '')[:100] + '...' if ref.get('content') else '',
                'similarity': ref.get('similarity', 0),
                'chunk_id': ref.get('id', '')
            })
    
    return formatted_refs


def create_test_client() -> RAGFlowSimpleClient:
    """Create a test client for development"""
    API_KEY = "ragflow-VjNjM4Zjk0NmMyZDExZjA4MjQyNTY3YT"
    BASE_URL = "http://127.0.0.1:9380"
    
    return RAGFlowSimpleClient(api_key=API_KEY, base_url=BASE_URL)


# Test the client if run directly
if __name__ == "__main__":
    print("Testing RAGFlow Simple Client...")
    
    try:
        client = create_test_client()
        
        # Test connection
        conn_result = client.test_connection()
        print(f"Connection test: {conn_result}")
        
        # Test assistant info
        assistant_info = client.get_assistant_info()
        print(f"Assistant info: {assistant_info}")
        
        # Test session creation
        session = client.create_session("Test Session")
        print(f"Created session: {session.session_id}")
        
        # Test sending a message
        print("\nSending test message...")
        for response in client.send_message(session.session_id, "Hello! What can you help me with?"):
            print(f"Response: {response.content}")
            if response.references:
                print(f"References: {len(response.references)} items")
        
        # Clean up
        client.delete_session(session.session_id)
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"Test failed: {e}")