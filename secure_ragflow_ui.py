#!/usr/bin/env python3
"""
Secure RAGFlow ChatBot UI with User Session Management
A secure Streamlit interface with proper user isolation
"""

import streamlit as st
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from user_session_manager import UserSessionManager, UserChat, create_manager


def init_session_state():
    """Initialize Streamlit session state variables"""
    if "session_manager" not in st.session_state:
        st.session_state.session_manager = create_manager()
    
    if "current_user_id" not in st.session_state:
        st.session_state.current_user_id = None
    
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = None
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "show_references" not in st.session_state:
        st.session_state.show_references = False


def load_chat_messages():
    """Load stored messages for the current chat"""
    if not st.session_state.current_user_id or not st.session_state.current_chat_id:
        st.session_state.messages = []
        return
    
    try:
        # Get stored messages from the session manager
        stored_messages = st.session_state.session_manager.get_chat_messages(
            st.session_state.current_user_id,
            st.session_state.current_chat_id
        )
        
        # Convert StoredMessage objects to Streamlit message format
        st.session_state.messages = []
        for stored_msg in stored_messages:
            message_dict = {
                "role": stored_msg.role,
                "content": stored_msg.content,
                "timestamp": stored_msg.timestamp.isoformat()
            }
            
            # Add references if available
            if stored_msg.references:
                message_dict["references"] = stored_msg.references
            
            st.session_state.messages.append(message_dict)
            
        print(f"✅ Loaded {len(st.session_state.messages)} messages for chat {st.session_state.current_chat_id}")
        
    except Exception as e:
        print(f"❌ Error loading chat messages: {e}")
        st.session_state.messages = []


def user_authentication():
    """Simple user authentication interface"""
    st.sidebar.markdown("### 👤 User Authentication")
    
    # User ID input
    user_id = st.sidebar.text_input(
        "Enter Your User ID:",
        value=st.session_state.current_user_id or "",
        placeholder="e.g., alice, bob, researcher_123",
        help="This identifies you and keeps your chats separate from other users"
    )
    
    if st.sidebar.button("🔑 Login", type="primary"):
        if user_id and user_id.strip():
            st.session_state.current_user_id = user_id.strip()
            st.session_state.current_chat_id = None  # Reset chat selection
            st.session_state.messages = []
            st.rerun()
        else:
            st.sidebar.error("Please enter a valid User ID")
    
    if st.session_state.current_user_id:
        st.sidebar.success(f"✅ Logged in as: **{st.session_state.current_user_id}**")
        
        if st.sidebar.button("🚪 Logout"):
            st.session_state.current_user_id = None
            st.session_state.current_chat_id = None
            st.session_state.messages = []
            st.rerun()
    
    return st.session_state.current_user_id is not None


def display_user_stats():
    """Display user statistics in the sidebar"""
    if not st.session_state.current_user_id:
        return
    
    try:
        stats = st.session_state.session_manager.get_user_stats(st.session_state.current_user_id)
        
        st.sidebar.markdown("### 📊 Your Stats")
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            st.metric("Total Chats", stats['total_chats'])
        
        with col2:
            st.metric("Total Messages", stats['total_messages'])
        
    except Exception as e:
        st.sidebar.error(f"Error loading stats: {e}")


def chat_management():
    """Chat creation and selection interface"""
    if not st.session_state.current_user_id:
        return None
    
    st.sidebar.markdown("### 💬 Your Chats")
    
    # Create new chat
    with st.sidebar.container():
        new_chat_title = st.text_input(
            "New Chat Title:",
            placeholder="e.g., Protein Questions, Data Analysis",
            key="new_chat_input"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Create Chat", type="primary"):
                if new_chat_title and new_chat_title.strip():
                    try:
                        new_chat = st.session_state.session_manager.create_user_chat(
                            st.session_state.current_user_id,
                            new_chat_title.strip()
                        )
                        st.session_state.current_chat_id = new_chat.chat_id
                        # Load messages for the new chat (should be empty)
                        load_chat_messages()
                        st.success(f"Created chat: {new_chat_title}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to create chat: {e}")
                else:
                    st.error("Please enter a chat title")
    
    # List existing chats
    try:
        user_chats = st.session_state.session_manager.list_user_chats(st.session_state.current_user_id)
        
        if not user_chats:
            st.sidebar.info("No chats yet. Create your first chat above!")
            return None
        
        # Chat selection
        st.sidebar.markdown("**Select a Chat:**")
        
        for chat in user_chats:
            # Create a container for each chat
            chat_container = st.sidebar.container()
            
            with chat_container:
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Chat selection button
                    chat_selected = st.session_state.current_chat_id == chat.chat_id
                    button_type = "primary" if chat_selected else "secondary"
                    
                    if st.button(
                        f"{'🔹' if chat_selected else '💬'} {chat.title}",
                        key=f"select_chat_{chat.chat_id}",
                        type=button_type,
                        use_container_width=True
                    ):
                        st.session_state.current_chat_id = chat.chat_id
                        # Load stored messages for this chat
                        load_chat_messages()
                        st.rerun()
                
                with col2:
                    # Delete chat button
                    if st.button("🗑️", key=f"delete_chat_{chat.chat_id}", help="Delete this chat"):
                        if st.session_state.session_manager.delete_user_chat(
                            st.session_state.current_user_id,
                            chat.chat_id
                        ):
                            if st.session_state.current_chat_id == chat.chat_id:
                                st.session_state.current_chat_id = None
                                st.session_state.messages = []
                            st.success(f"Deleted chat: {chat.title}")
                            st.rerun()
                        else:
                            st.error("Failed to delete chat")
                
                # Show chat info
                if chat_selected:
                    st.sidebar.caption(f"Created: {chat.created_at.strftime('%Y-%m-%d %H:%M')}")
                    st.sidebar.caption(f"Messages: {chat.message_count}")
        
        return st.session_state.current_chat_id
        
    except Exception as e:
        st.sidebar.error(f"Error loading chats: {e}")
        return None


def display_main_interface():
    """Display the main chat interface"""
    if not st.session_state.current_user_id:
        st.markdown("""
        # 🔐 Secure RAGFlow ChatBot
        
        Welcome to the secure RCSB PDB ChatBot! This interface provides proper user isolation 
        to ensure your conversations remain private.
        
        ## 🚀 Getting Started
        1. **Enter your User ID** in the sidebar to login
        2. **Create a new chat** for your questions
        3. **Start chatting** about protein structures, PDB data, and more!
        
        ## 🔒 Security Features
        - ✅ **User Isolation**: Your chats are completely separate from other users
        - ✅ **Private Sessions**: Each chat gets its own secure session
        - ✅ **Data Separation**: Your data is stored separately from other users
        - ✅ **Session Security**: No cross-user access or data leakage
        
        ## 💡 Tips
        - Use descriptive chat titles like "Protein Analysis" or "Structure Questions"
        - Create separate chats for different topics or projects
        - Your chats are automatically saved and can be resumed anytime
        """)
        return
    
    if not st.session_state.current_chat_id:
        st.markdown(f"""
        # 👋 Welcome, {st.session_state.current_user_id}!
        
        ## 🎯 Next Steps
        1. **Create your first chat** using the sidebar
        2. **Give it a descriptive title** like "Protein Questions" or "Research Help"
        3. **Start chatting** with the RCSB PDB assistant!
        
        ## 🤖 What You Can Ask About
        - **Protein Data Bank (PDB)** structures and data
        - **Crystallography** and structure determination
        - **Molecular biology** and protein science
        - **Data analysis** and bioinformatics
        - **Structure deposition** and validation
        """)
        return
    
    # Get current chat info
    current_chat = st.session_state.session_manager.get_user_chat(
        st.session_state.current_user_id,
        st.session_state.current_chat_id
    )
    
    if not current_chat:
        st.error("Chat not found. Please select a different chat.")
        return
    
    # Chat header
    st.markdown(f"# 💬 {current_chat.title}")
    st.caption(f"User: {st.session_state.current_user_id} | Created: {current_chat.created_at.strftime('%Y-%m-%d %H:%M')}")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            
            # Show references if available and enabled
            if (message["role"] == "assistant" and 
                st.session_state.show_references and 
                message.get("references")):
                
                with st.expander("📚 References"):
                    for ref in message["references"]:
                        st.markdown(f"**{ref.get('document_name', 'Unknown')}**")
                        st.caption(f"Similarity: {ref.get('similarity', 0):.2f}")
                        st.text(ref.get('content', '')[:200] + "...")
    
    # Chat input
    if prompt := st.chat_input("Ask about RCSB PDB, protein structures, or anything related..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.write(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            references = []
            
            try:
                # Stream response from RAGFlow
                for response_chunk in st.session_state.session_manager.send_message_to_chat(
                    st.session_state.current_user_id,
                    st.session_state.current_chat_id,
                    prompt
                ):
                    # Update the message as it streams
                    if response_chunk.content != full_response:
                        full_response = response_chunk.content
                        message_placeholder.write(full_response)
                    
                    # Capture references from the final response
                    if response_chunk.references:
                        references = response_chunk.references
                
                # Add assistant message to chat history
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": full_response,
                    "references": references
                })
                
                # Show references if enabled
                if st.session_state.show_references and references:
                    with st.expander("📚 References"):
                        for ref in references:
                            st.markdown(f"**{ref.get('document_name', 'Unknown')}**")
                            st.caption(f"Similarity: {ref.get('similarity', 0):.2f}")
                            st.text(ref.get('content', '')[:200] + "...")
                
            except Exception as e:
                st.error(f"Error getting response: {e}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Sorry, I encountered an error: {e}"
                })


def sidebar_settings():
    """Display settings in the sidebar"""
    if not st.session_state.current_user_id:
        return
    
    st.sidebar.markdown("### ⚙️ Settings")
    
    # References toggle
    st.session_state.show_references = st.sidebar.checkbox(
        "📚 Show References",
        value=st.session_state.show_references,
        help="Display source documents and similarity scores"
    )
    
    # Export functionality
    if st.sidebar.button("📤 Export Current Chat"):
        if st.session_state.messages:
            # Create export content
            export_content = f"# Chat Export: {st.session_state.current_user_id}\n"
            export_content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            for msg in st.session_state.messages:
                role = "You" if msg["role"] == "user" else "Assistant"
                export_content += f"**{role}:** {msg['content']}\n\n"
            
            st.sidebar.download_button(
                label="💾 Download Chat",
                data=export_content,
                file_name=f"chat_export_{st.session_state.current_user_id}_{int(time.time())}.txt",
                mime="text/plain"
            )
        else:
            st.sidebar.info("No messages to export")
    
    # Clear chat functionality
    if st.sidebar.button("🧽 Clear Current Chat", help="Clear all messages in current chat"):
        if st.session_state.current_chat_id and st.session_state.messages:
            if st.session_state.session_manager.clear_chat_messages(
                st.session_state.current_user_id,
                st.session_state.current_chat_id
            ):
                st.session_state.messages = []
                st.sidebar.success("Chat cleared!")
                st.rerun()
            else:
                st.sidebar.error("Failed to clear chat")
        else:
            st.sidebar.info("No messages to clear")


def main():
    """Main application function"""
    # Page configuration
    st.set_page_config(
        page_title="Secure RAGFlow ChatBot",
        page_icon="🔐",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main > div {
        padding-top: 2rem;
    }
    .stButton > button {
        width: 100%;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #e3f2fd;
    }
    .assistant-message {
        background-color: #f3f4f6;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    init_session_state()
    
    # Sidebar components
    is_authenticated = user_authentication()
    
    if is_authenticated:
        display_user_stats()
        current_chat = chat_management()
        sidebar_settings()
        
        # Admin section (if needed)
        if st.sidebar.checkbox("🔧 Admin Mode", help="Show administrative options"):
            st.sidebar.markdown("### 🛠️ Admin Tools")
            
            all_users = st.session_state.session_manager.list_all_users()
            st.sidebar.info(f"Total users: {len(all_users)}")
            
            if st.sidebar.button("🧹 Cleanup Test Data", help="Remove test users"):
                test_users = ["alice", "bob", "charlie"]
                for user in test_users:
                    if user in all_users:
                        st.session_state.session_manager.cleanup_user_data(user)
                st.sidebar.success("Cleaned up test data")
    
    # Main interface
    display_main_interface()
    
    # Footer
    if is_authenticated:
        st.sidebar.markdown("---")
        st.sidebar.markdown("""
        ### 🔒 Security Notice
        Your conversations are private and isolated from other users. 
        Each chat creates a separate secure session.
        """)


if __name__ == "__main__":
    main()