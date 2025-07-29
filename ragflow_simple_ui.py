"""
RAGFlow Simple ChatBot UI
A clean Streamlit interface for the 'RCSB ChatBot v2' assistant
"""

import streamlit as st
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid

# Import our simplified client
from ragflow_simple_client import RAGFlowSimpleClient, ChatMessage, ChatSession, extract_references

# Configuration
API_KEY = "ragflow-VjNjM4Zjk0NmMyZDExZjA4MjQyNTY3YT"  # Your provided API key
BASE_URL = "http://127.0.0.1:9380"
CONVERSATIONS_FILE = "ragflow_conversations.json"

# Page configuration
st.set_page_config(
    page_title="RCSB ChatBot v2",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (keeping the excellent styling from your original design)
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        border-radius: 20px;
        height: 3em;
        background-color: #f0f2f6;
        color: #262730;
        border: 1px solid #e0e2e6;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        background-color: #e0e2e6;
        border-color: #d0d2d6;
        transform: translateY(-1px);
    }
    
    /* Chat message styles */
    .chat-message {
        padding: 1rem;
        border-radius: 0.75rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .user-message {
        background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
        border-left: 4px solid #1f77b4;
        margin-left: 2rem;
    }
    .assistant-message {
        background: linear-gradient(135deg, #f5f5f5 0%, #fafafa 100%);
        border-left: 4px solid #4caf50;
        margin-right: 2rem;
    }
    .error-message {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
    }
    
    /* Status indicators */
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }
    .status-connected {
        background-color: #4caf50;
        animation: pulse 2s infinite;
    }
    .status-disconnected {
        background-color: #f44336;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    /* Session management */
    .session-item {
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
        cursor: pointer;
        transition: all 0.2s;
        background-color: #f8f9fa;
        border: 1px solid #e0e2e6;
    }
    .session-item:hover {
        background-color: #e3f2fd;
        border-color: #1f77b4;
        transform: translateX(5px);
    }
    .session-item.active {
        background-color: #e3f2fd;
        border-color: #1f77b4;
        border-width: 2px;
    }
    
    /* Streaming indicator */
    .streaming-indicator {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 0.9em;
        color: #666;
    }
    .streaming-dot {
        width: 4px;
        height: 4px;
        border-radius: 50%;
        background-color: #1f77b4;
        animation: streaming 1.5s infinite;
    }
    .streaming-dot:nth-child(2) { animation-delay: 0.5s; }
    .streaming-dot:nth-child(3) { animation-delay: 1s; }
    
    @keyframes streaming {
        0%, 80%, 100% { transform: scale(0); }
        40% { transform: scale(1); }
    }
    
    /* Hide streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Session state initialization
def init_session_state():
    """Initialize session state variables"""
    defaults = {
        'ragflow_client': None,
        'current_session': None,
        'conversation_messages': [],
        'connection_status': 'disconnected',
        'assistant_info': {},
        'available_sessions': [],
        'last_response': None,
        'show_references': False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Conversation persistence
def load_conversations() -> Dict[str, Any]:
    """Load conversations from JSON file"""
    if os.path.exists(CONVERSATIONS_FILE):
        try:
            with open(CONVERSATIONS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading conversations: {e}")
            return {}
    return {}

def save_conversations(conversations: Dict[str, Any]):
    """Save conversations to JSON file"""
    try:
        with open(CONVERSATIONS_FILE, 'w') as f:
            json.dump(conversations, f, indent=2, default=str)
    except Exception as e:
        st.error(f"Error saving conversations: {e}")

def save_current_conversation():
    """Save current conversation to file"""
    if not st.session_state.current_session or not st.session_state.conversation_messages:
        return
    
    conversations = load_conversations()
    session_id = st.session_state.current_session.session_id
    
    conversations[session_id] = {
        'session_name': st.session_state.current_session.name,
        'session_id': session_id,
        'created_at': st.session_state.current_session.created_at.isoformat(),
        'messages': [
            {
                'content': msg.content,
                'role': msg.role,
                'timestamp': msg.timestamp.isoformat(),
                'references': msg.references
            }
            for msg in st.session_state.conversation_messages
        ]
    }
    
    save_conversations(conversations)

# RAGFlow client management
@st.cache_resource
def get_ragflow_client():
    """Get cached RAGFlow client"""
    try:
        return RAGFlowSimpleClient(api_key=API_KEY, base_url=BASE_URL)
    except Exception as e:
        st.error(f"Failed to initialize RAGFlow client: {e}")
        return None

def test_connection():
    """Test RAGFlow connection"""
    client = get_ragflow_client()
    if not client:
        st.session_state.connection_status = 'disconnected'
        return False
    
    try:
        result = client.test_connection()
        if result['success']:
            st.session_state.connection_status = 'connected'
            st.session_state.ragflow_client = client
            st.session_state.assistant_info = client.get_assistant_info()
            return True
        else:
            st.session_state.connection_status = 'disconnected'
            return False
    except Exception as e:
        st.session_state.connection_status = 'disconnected'
        st.error(f"Connection test failed: {e}")
        return False

def load_available_sessions():
    """Load available sessions from RAGFlow"""
    if not st.session_state.ragflow_client:
        return
    
    try:
        sessions = st.session_state.ragflow_client.list_sessions(limit=20)
        st.session_state.available_sessions = sessions
    except Exception as e:
        st.error(f"Failed to load sessions: {e}")

def create_new_session():
    """Create a new chat session"""
    if not st.session_state.ragflow_client:
        st.error("No connection to RAGFlow")
        return
    
    try:
        session_name = f"Chat Session {int(time.time())}"
        session = st.session_state.ragflow_client.create_session(session_name)
        
        st.session_state.current_session = session
        st.session_state.conversation_messages = session.messages.copy()
        
        # Refresh available sessions
        load_available_sessions()
        
        st.success(f"Created new session: {session.name}")
        
    except Exception as e:
        st.error(f"Failed to create session: {e}")

def switch_to_session(session_id: str, session_name: str):
    """Switch to an existing session"""
    # Save current conversation first
    save_current_conversation()
    
    # Load conversation from file if available
    conversations = load_conversations()
    
    if session_id in conversations:
        # Load from saved conversation
        conv_data = conversations[session_id]
        messages = []
        
        for msg_data in conv_data['messages']:
            messages.append(ChatMessage(
                content=msg_data['content'],
                role=msg_data['role'],
                timestamp=datetime.fromisoformat(msg_data['timestamp']),
                references=msg_data.get('references')
            ))
        
        st.session_state.conversation_messages = messages
    else:
        # New session, start fresh
        st.session_state.conversation_messages = []
    
    # Create session object
    st.session_state.current_session = ChatSession(
        session_id=session_id,
        name=session_name,
        chat_id=st.session_state.assistant_info.get('id', ''),
        created_at=datetime.now(),
        messages=st.session_state.conversation_messages
    )

def send_message(user_message: str):
    """Send message to RAGFlow and handle response"""
    if not st.session_state.ragflow_client or not st.session_state.current_session:
        st.error("No active session")
        return
    
    # Add user message to conversation
    user_msg = ChatMessage(
        content=user_message,
        role='user',
        timestamp=datetime.now()
    )
    st.session_state.conversation_messages.append(user_msg)
    
    # Create placeholder for assistant response
    response_placeholder = st.empty()
    streaming_placeholder = st.empty()
    
    try:
        # Show streaming indicator
        with streaming_placeholder.container():
            st.markdown(
                '<div class="streaming-indicator">RCSB ChatBot is thinking<span class="streaming-dot"></span><span class="streaming-dot"></span><span class="streaming-dot"></span></div>',
                unsafe_allow_html=True
            )
        
        # Send message and get streaming response
        full_response = ""
        assistant_msg = None
        
        for response_chunk in st.session_state.ragflow_client.send_message(
            st.session_state.current_session.session_id,
            user_message,
            stream=True
        ):
            full_response = response_chunk.content
            assistant_msg = response_chunk
            
            # Update response placeholder
            with response_placeholder.container():
                st.markdown(
                    f'<div class="chat-message assistant-message"><strong>🧬 RCSB ChatBot v2:</strong><br>{full_response}</div>',
                    unsafe_allow_html=True
                )
        
        # Clear streaming indicator
        streaming_placeholder.empty()
        
        # Add final response to conversation
        if assistant_msg:
            st.session_state.conversation_messages.append(assistant_msg)
            st.session_state.last_response = assistant_msg
            
            # Save conversation
            save_current_conversation()
        
    except Exception as e:
        streaming_placeholder.empty()
        response_placeholder.empty()
        st.error(f"Failed to send message: {e}")

def render_sidebar():
    """Render the sidebar"""
    with st.sidebar:
        st.header("🧬 RCSB ChatBot v2")
        
        # Connection status
        status_class = 'status-connected' if st.session_state.connection_status == 'connected' else 'status-disconnected'
        st.markdown(
            f'<div><span class="status-indicator {status_class}"></span>Status: {st.session_state.connection_status.title()}</div>',
            unsafe_allow_html=True
        )
        
        # Connection test button
        if st.button("🔄 Test Connection", use_container_width=True):
            with st.spinner("Testing connection..."):
                if test_connection():
                    st.success("✅ Connected to RAGFlow!")
                    load_available_sessions()
                else:
                    st.error("❌ Connection failed!")
        
        # Assistant info
        if st.session_state.assistant_info:
            st.markdown("---")
            st.subheader("🤖 Assistant Info")
            st.write(f"**Name:** {st.session_state.assistant_info.get('name', 'Unknown')}")
            st.write(f"**ID:** {st.session_state.assistant_info.get('id', 'Unknown')[:8]}...")
            datasets = st.session_state.assistant_info.get('dataset_ids', [])
            st.write(f"**Datasets:** {', '.join(datasets) if datasets else 'None'}")
        
        st.markdown("---")
        
        # Session management
        st.subheader("💬 Chat Sessions")
        
        # New session button
        if st.button("➕ New Session", use_container_width=True, type="primary"):
            create_new_session()
            st.rerun()
        
        # List available sessions
        if st.session_state.available_sessions:
            st.write("**Available Sessions:**")
            
            for session in st.session_state.available_sessions[:10]:  # Show first 10
                is_active = (st.session_state.current_session and 
                           st.session_state.current_session.session_id == session['id'])
                
                button_type = "primary" if is_active else "secondary"
                
                if st.button(
                    f"{'🟢' if is_active else '⚪'} {session['name'][:30]}...",
                    key=f"session_{session['id']}",
                    use_container_width=True,
                    type=button_type
                ):
                    switch_to_session(session['id'], session['name'])
                    st.rerun()
        
        st.markdown("---")
        
        # Settings
        st.subheader("⚙️ Settings")
        
        st.session_state.show_references = st.checkbox(
            "Show References",
            value=st.session_state.show_references,
            help="Display source references in responses"
        )
        
        # Refresh sessions button
        if st.button("🔄 Refresh Sessions"):
            load_available_sessions()
            st.rerun()

def render_chat_interface():
    """Render the main chat interface"""
    # Check connection
    if st.session_state.connection_status != 'connected':
        st.warning("⚠️ Not connected to RAGFlow. Please test the connection first.")
        return
    
    # Check active session
    if not st.session_state.current_session:
        st.info("💬 Create a new session or select an existing one to start chatting.")
        return
    
    # Display current session info
    st.subheader(f"💬 {st.session_state.current_session.name}")
    st.caption(f"Session ID: {st.session_state.current_session.session_id[:8]}...")
    
    # Display conversation
    for message in st.session_state.conversation_messages:
        if message.role == 'user':
            st.markdown(
                f'<div class="chat-message user-message"><strong>👤 You:</strong><br>{message.content}</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="chat-message assistant-message"><strong>🧬 RCSB ChatBot v2:</strong><br>{message.content}</div>',
                unsafe_allow_html=True
            )
            
            # Show references if enabled
            if st.session_state.show_references and message.references:
                with st.expander(f"📚 References ({len(message.references)} items)"):
                    refs = extract_references(message)
                    for i, ref in enumerate(refs, 1):
                        st.write(f"**{i}. {ref['document_name']}**")
                        st.write(f"Content: {ref['content']}")
                        st.write(f"Similarity: {ref['similarity']:.3f}")
                        st.markdown("---")
    
    # Chat input
    st.markdown("---")
    
    # Quick start questions
    if not st.session_state.conversation_messages:
        st.subheader("🚀 Quick Start")
        st.write("Try these questions about RCSB PDB:")
        
        quick_questions = [
            "What is RCSB PDB?",
            "How do I search for protein structures?",
            "What file formats are available for download?",
            "How do I deposit a structure to the PDB?"
        ]
        
        cols = st.columns(2)
        for i, question in enumerate(quick_questions):
            with cols[i % 2]:
                if st.button(question, key=f"quick_{i}", use_container_width=True):
                    send_message(question)
                    st.rerun()
    
    # Main chat input
    with st.form("chat_form", clear_on_submit=True):
        col1, col2 = st.columns([6, 1])
        
        with col1:
            user_input = st.text_input(
                "Ask about RCSB PDB:",
                placeholder="Type your question about protein structures, crystallography, or the PDB database...",
                label_visibility="collapsed"
            )
        
        with col2:
            submit = st.form_submit_button("Send", use_container_width=True)
        
        if submit and user_input:
            send_message(user_input)
            st.rerun()

def render_export_section():
    """Render export functionality"""
    if st.session_state.current_session and st.session_state.conversation_messages:
        st.markdown("---")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("📤 Export Chat", use_container_width=True):
                # Create export text
                export_text = f"RCSB ChatBot v2 Conversation Export\n"
                export_text += f"Session: {st.session_state.current_session.name}\n"
                export_text += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                export_text += "=" * 50 + "\n\n"
                
                for msg in st.session_state.conversation_messages:
                    timestamp = msg.timestamp.strftime('%H:%M:%S')
                    role = "USER" if msg.role == 'user' else "ASSISTANT"
                    export_text += f"[{timestamp}] {role}: {msg.content}\n\n"
                
                st.download_button(
                    label="Download",
                    data=export_text,
                    file_name=f"rcsb_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )
        
        with col2:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.conversation_messages = []
                save_current_conversation()
                st.rerun()

def main():
    """Main application function"""
    # Initialize session state
    init_session_state()
    
    # Auto-connect on first load
    if st.session_state.connection_status == 'disconnected':
        test_connection()
        if st.session_state.connection_status == 'connected':
            load_available_sessions()
    
    # Header
    st.title("🧬 RCSB ChatBot v2")
    st.caption("Ask questions about protein structures, crystallography, and the Protein Data Bank")
    
    # Render sidebar
    render_sidebar()
    
    # Main interface
    render_chat_interface()
    
    # Export section
    render_export_section()

if __name__ == "__main__":
    main()