#!/usr/bin/env python3
"""
RCSB PDB ChatBot - Intelligent Assistant for Structural Biology
A professional Streamlit interface for protein structure research and PDB data queries
"""

import streamlit as st
import time
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

# Using Streamlit's built-in st.markdown for all markdown processing

from user_session_manager import UserSessionManager, UserChat, create_manager
from ragflow_assistant_manager import create_default_assistant_config


def process_markdown_response(content: str) -> str:
    """
    Extract markdown content from code blocks if wrapped in ```markdown blocks
    
    Args:
        content: The response content, potentially wrapped in ```markdown blocks
        
    Returns:
        Extracted markdown content ready for st.markdown() display
    """
    if not content:
        return content
    
    # Check if content is wrapped in markdown code blocks
    markdown_pattern = r'^```markdown\s*\n(.*?)\n```$'
    match = re.match(markdown_pattern, content.strip(), re.DOTALL)
    
    if match:
        # Extract and return the markdown content
        return match.group(1)
    
    # If not wrapped in code blocks, return as-is
    return content


def display_message_feedback_ui(message: Dict[str, Any], message_index: int = 0):
    """
    Display feedback UI for an assistant message using Streamlit's built-in widgets

    Args:
        message: Message dictionary containing role, content, timestamp, etc.
        message_index: Index of the message for unique key generation
    """
    if message["role"] != "assistant":
        return

    # Get message timestamp for unique identification
    message_timestamp = message.get("timestamp")
    if not message_timestamp:
        # For backward compatibility, generate timestamp from content hash + index
        import hashlib
        content_hash = hashlib.md5(f"{message['content']}{message.get('role', 'unknown')}{message_index}".encode()).hexdigest()[:8]
        message_timestamp = f"legacy_{content_hash}"
    
    # Unique keys for widgets
    feedback_key = f"feedback_{message_timestamp}"
    comment_key = f"comment_{message_timestamp}"
    expand_key = f"expand_comment_{message_timestamp}"
    categories_key = f"categories_{message_timestamp}"
    
    # Check if feedback already exists
    existing_feedback = None
    if (st.session_state.current_user_id and 
        st.session_state.current_chat_id and 
        hasattr(st.session_state, 'session_manager')):
        existing_feedback = st.session_state.session_manager.get_message_feedback(
            st.session_state.current_user_id,
            st.session_state.current_chat_id,
            message_timestamp
        )
    
    # Feedback section header
    st.markdown("---")
    
    # Main feedback row
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        # Streamlit's built-in thumbs up/down feedback widget
        current_rating = None
        if existing_feedback:
            current_rating = existing_feedback.get("rating")
        
        feedback_score = st.feedback(
            "thumbs", 
            key=feedback_key
        )
        
        # Convert feedback score to our format
        rating_value = None
        if feedback_score == 1:
            rating_value = "thumbs-up"
        elif feedback_score == 0:
            rating_value = "thumbs-down"
    
    with col2:
        # Comment toggle button
        if f"show_comment_{message_timestamp}" not in st.session_state:
            st.session_state[f"show_comment_{message_timestamp}"] = False
        
        if st.button("💬 Comment", key=f"comment_btn_{message_timestamp}", help="Add optional comment"):
            st.session_state[f"show_comment_{message_timestamp}"] = not st.session_state[f"show_comment_{message_timestamp}"]
    
    with col3:
        # Save feedback button
        save_feedback = st.button("💾 Save", key=f"save_{message_timestamp}", help="Save your feedback")
    
    # Expandable comment section
    if st.session_state.get(f"show_comment_{message_timestamp}", False):
        with st.container():
            st.markdown("**Optional Feedback:**")
            
            # Categories
            feedback_categories = st.multiselect(
                "Select categories:",
                options=["helpful", "accurate", "clear", "complete", "relevant", "confusing", "incorrect", "incomplete", "off-topic"],
                default=existing_feedback.get("categories", []) if existing_feedback else [],
                key=categories_key,
                help="Choose categories that describe this response"
            )
            
            # Text comment
            comment_text = st.text_area(
                "Your comment (optional):",
                value=existing_feedback.get("comment", "") if existing_feedback else "",
                key=comment_key,
                help="Add any specific feedback about this response"
            )
    
    # Save feedback when button is clicked
    if save_feedback and rating_value is not None:
        feedback_data = {
            "rating": rating_value,
            "feedback_timestamp": datetime.now().isoformat()
        }
        
        # Add categories and comment if provided
        if st.session_state.get(f"show_comment_{message_timestamp}", False):
            if st.session_state.get(categories_key):
                feedback_data["categories"] = st.session_state[categories_key]
            if st.session_state.get(comment_key):
                feedback_data["comment"] = st.session_state[comment_key]
        
        # Save to session manager
        if (st.session_state.current_user_id and 
            st.session_state.current_chat_id and 
            hasattr(st.session_state, 'session_manager')):
            
            success = st.session_state.session_manager.add_message_feedback(
                st.session_state.current_user_id,
                st.session_state.current_chat_id,
                message_timestamp,
                feedback_data
            )
            
            if success:
                st.success("✅ Feedback saved!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to save feedback")
    
    elif save_feedback and rating_value is None:
        st.warning("⚠️ Please select thumbs up or thumbs down first")
    
    # Show existing feedback summary
    if existing_feedback:
        st.caption(f"📊 Feedback: {existing_feedback.get('rating', 'N/A').replace('-', ' ').title()}" + 
                  (f" | Categories: {', '.join(existing_feedback.get('categories', []))}" if existing_feedback.get('categories') else "") +
                  (f" | Comment: {existing_feedback.get('comment', '')[:50]}{'...' if len(existing_feedback.get('comment', '')) > 50 else ''}" if existing_feedback.get('comment') else ""))


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
    
    if "editor_mode" not in st.session_state:
        st.session_state.editor_mode = False


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
            st.sidebar.error("Please enter a research ID")
    
    if st.session_state.current_user_id:
        st.sidebar.success(f"✅ Research session: **{st.session_state.current_user_id}**")
        
        if st.sidebar.button("📚 End Session"):
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


def display_fullscreen_prompt_editor():
    """Display full-screen prompt editor in the main area"""
    if not hasattr(st.session_state.session_manager, 'assistant_config'):
        st.error("❌ Assistant configuration not available")
        return
    
    config = st.session_state.session_manager.assistant_config
    
    # Header with navigation and info
    col_nav, col_info, col_actions = st.columns([2, 2, 1])
    
    with col_nav:
        st.markdown("# 🖥️ Full-Screen Prompt Editor")
    
    with col_info:
        st.metric("Character Count", len(config.system_prompt))
    
    with col_actions:
        if st.button("↩️ Back to Chat", type="secondary", use_container_width=True):
            st.session_state.editor_mode = False
            st.rerun()
    
    st.divider()
    
    # Full-screen editor with custom styling
    st.markdown("""
    <style>
    .fullscreen-editor .stTextArea > div > div > textarea {
        font-family: 'Monaco', 'Consolas', 'Courier New', monospace;
        font-size: 14px;
        line-height: 1.5;
        border-radius: 8px;
        border: 2px solid #e0e0e0;
        padding: 16px;
    }
    .fullscreen-editor .stTextArea > div > div > textarea:focus {
        border-color: #1976d2;
        box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.1);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Main editor area
    with st.container():
        st.markdown('<div class="fullscreen-editor">', unsafe_allow_html=True)
        
        new_prompt = st.text_area(
            "System Prompt Content",
            value=config.system_prompt,
            height=500,  # Much larger height for full-screen
            help="Edit your system prompt with full screen real estate. Use monospace font for better readability.",
            key="fullscreen_prompt_editor",
            label_visibility="collapsed"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Action buttons at the bottom
    st.divider()
    
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])
    
    with col1:
        if st.button("💾 Save Changes", type="primary", use_container_width=True):
            if new_prompt.strip() and new_prompt != config.system_prompt:
                with st.spinner("Updating assistant prompt..."):
                    success = st.session_state.session_manager.assistant_manager.update_prompt(new_prompt.strip())
                    if success:
                        st.session_state.session_manager.assistant_config.system_prompt = new_prompt.strip()
                        st.success("✅ Prompt updated successfully!")
                        time.sleep(1.5)
                        st.session_state.editor_mode = False  # Return to chat after saving
                        st.rerun()
                    else:
                        st.error("❌ Failed to update prompt")
            elif new_prompt == config.system_prompt:
                st.info("ℹ️ No changes detected")
            else:
                st.error("❌ Prompt cannot be empty")
    
    with col2:
        if st.button("↺ Reset to Default", use_container_width=True):
            from ragflow_assistant_manager import create_default_assistant_config
            default_config = create_default_assistant_config()
            # Reset the assistant prompt directly instead of modifying session state
            success = st.session_state.session_manager.assistant_manager.update_prompt(default_config.system_prompt)
            if success:
                st.session_state.session_manager.assistant_config.system_prompt = default_config.system_prompt
                st.success("✅ Reset to default prompt!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to reset prompt")
    
    with col3:
        if st.button("📋 Copy to Clipboard", use_container_width=True):
            # JavaScript copy functionality
            st.write("📋 Use Ctrl+A, Ctrl+C to copy the prompt text")
    
    with col4:
        if st.button("🔍 Check Health", use_container_width=True):
            with st.spinner("Checking RAGFlow connection..."):
                health = st.session_state.session_manager.assistant_manager.health_check()
                if all(health.values()):
                    st.success("✅ All systems operational")
                else:
                    st.warning(f"⚠️ Issues detected: {health}")
    
    with col5:
        # Info panel
        st.info("💡 **Tip**: Use this full-screen editor for comfortable editing of long prompts. Changes are saved to RAGFlow immediately.")
    
    # Additional tools section
    with st.expander("📊 Prompt Analysis", expanded=False):
        col_analysis1, col_analysis2, col_analysis3 = st.columns(3)
        
        with col_analysis1:
            lines = len(new_prompt.split('\n'))
            st.metric("Lines", lines)
        
        with col_analysis2:
            words = len(new_prompt.split())
            st.metric("Words", words)
        
        with col_analysis3:
            # Simple readability info
            avg_line_length = len(new_prompt) / max(lines, 1)
            st.metric("Avg Line Length", f"{avg_line_length:.0f}")
        
        # Static guidance
        st.info("💡 **Editing Tips**: Keep lines under 100 characters for readability. Use clear section headers with ## markdown.")


def display_main_interface():
    """Display the main chat interface or full-screen prompt editor"""
    
    # Check if we're in editor mode
    if st.session_state.get("editor_mode", False):
        display_fullscreen_prompt_editor()
        return
    
    if not st.session_state.current_user_id:
        st.markdown("""
        # 🧬 RCSB PDB ChatBot
        
        Your intelligent assistant for protein structures, crystallography, and structural biology data.
        
        ## 🚀 Getting Started
        1. **Enter your User ID** in the sidebar to get started
        2. **Create a new chat** with a descriptive title for your research topic
        3. **Ask questions** about protein structures, PDB data, crystallography, and more!
        
        ## 🔬 What You Can Ask About
        - **Protein Data Bank (PDB)** structures and entries
        - **Crystallography** and structure determination methods
        - **Molecular biology** and protein science concepts
        - **Data analysis** and structural bioinformatics
        - **Structure deposition** and validation processes
        - **wwPDB policies** and procedures
        
        ## 💡 Tips for Better Results
        - Use descriptive chat titles like "Protein Analysis Project" or "Crystal Structure Questions"
        - Create separate chats for different research topics or projects
        - Be specific in your questions for more accurate responses
        - Your conversations are automatically saved for future reference
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
    for message_index, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            # Process and render markdown content properly
            processed_content = process_markdown_response(message["content"])
            
            # Use Streamlit's built-in markdown rendering
            st.markdown(processed_content)
            
            # Show references if available and enabled
            if (message["role"] == "assistant" and 
                st.session_state.show_references and 
                message.get("references")):
                
                with st.expander("📚 References"):
                    for i, ref in enumerate(message["references"], 1):
                        st.markdown(f"**Reference {i}: {ref.get('document_name', 'Unknown')}**")
                        st.caption(f"Similarity Score: {ref.get('similarity', 0):.2f}")
                        
                        # Show full content with proper formatting
                        ref_content = ref.get('content', '')
                        if ref_content:
                            with st.container():
                                st.markdown("**Content:**")
                                st.markdown(ref_content, unsafe_allow_html=False)
                        else:
                            st.info("No content available for this reference")
                        
                        # Add separator between references
                        if i < len(message["references"]):
                            st.divider()
            
            # Add feedback UI for assistant messages
            if message["role"] == "assistant":
                display_message_feedback_ui(message, message_index)
    
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
                        
                        # Process and render markdown content during streaming
                        processed_content = process_markdown_response(full_response)
                        
                        # Use Streamlit's built-in markdown rendering
                        message_placeholder.markdown(processed_content)
                    
                    # Capture references from the final response
                    if response_chunk.references:
                        references = response_chunk.references
                
                # Add assistant message to chat history
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": full_response,
                    "references": references
                })
                
                # Show references if available
                if st.session_state.show_references and references:
                    with st.expander("📚 References"):
                        for i, ref in enumerate(references, 1):
                            st.markdown(f"**Reference {i}: {ref.get('document_name', 'Unknown')}**")
                            st.caption(f"Similarity Score: {ref.get('similarity', 0):.2f}")
                            
                            # Show full content with proper formatting
                            ref_content = ref.get('content', '')
                            if ref_content:
                                with st.container():
                                    st.markdown("**Content:**")
                                    st.markdown(ref_content, unsafe_allow_html=False)
                            else:
                                st.info("No content available for this reference")
                            
                            # Add separator between references
                            if i < len(references):
                                st.divider()
                
                # Add feedback UI for the new assistant message
                if full_response:
                    new_message = {
                        "role": "assistant",
                        "content": full_response,
                        "references": references,
                        "timestamp": datetime.now().isoformat()  # Add timestamp for feedback
                    }
                    display_message_feedback_ui(new_message, len(st.session_state.messages))
                
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
    
    # Always show references when available (removed checkbox)
    st.session_state.show_references = True
    
    # Advanced settings (only in debug mode)
    if os.getenv("DEBUG_MODE", "false").lower() == "true":
        with st.sidebar.expander("🔧 Advanced Settings"):
            
            # Configuration metrics (optional - controlled by env var)
            if os.getenv("SHOW_CONFIG_METRICS", "false").lower() == "true":
                if hasattr(st.session_state.session_manager, 'assistant_config'):
                    config = st.session_state.session_manager.assistant_config
                    
                    st.markdown("**Assistant Configuration:**")
                    
                    # Compact metrics display using containers
                    with st.container():
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Temperature", f"{config.temperature:.1f}")
                            st.metric("Top-P", f"{config.top_p:.1f}")
                        with col2:
                            st.metric("Top-N", config.top_n)
                            st.metric("Similarity", f"{config.similarity_threshold:.1f}")
                    
                    st.divider()
            
            # System Prompt Editor (controlled by env var)
            if os.getenv("SHOW_PROMPT_EDITOR", "false").lower() == "true":
                if hasattr(st.session_state.session_manager, 'assistant_config'):
                    config = st.session_state.session_manager.assistant_config
                    
                    st.markdown("**System Prompt Editor:**")
                    
                    # Compact header with character count and full-screen option
                    col_header, col_fullscreen = st.columns([2, 1])
                    with col_header:
                        st.caption(f"📝 Current length: {len(config.system_prompt)} characters")
                    with col_fullscreen:
                        if st.button("🖥️ Full Screen", key="fullscreen_edit", use_container_width=True, help="Open full-screen editor"):
                            st.session_state.editor_mode = True
                            st.rerun()
                    
                    # Single text area that shows current prompt for editing
                    new_prompt = st.text_area(
                        "Prompt Content:",
                        value=config.system_prompt,
                        height=250,
                        help="Modify the system prompt and save changes (or use Full Screen for better editing)",
                        key="prompt_editor",
                        label_visibility="collapsed"
                    )
                    
                    # Action buttons in horizontal layout
                    col_update, col_reset, col_health = st.columns(3)
                    
                    with col_update:
                        if st.button("💾 Save", type="primary", use_container_width=True):
                            if new_prompt.strip() and new_prompt != config.system_prompt:
                                with st.spinner("Updating..."):
                                    success = st.session_state.session_manager.assistant_manager.update_prompt(new_prompt.strip())
                                    if success:
                                        st.session_state.session_manager.assistant_config.system_prompt = new_prompt.strip()
                                        st.success("✅ Updated!")
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed")
                            elif new_prompt == config.system_prompt:
                                st.info("No changes")
                            else:
                                st.error("Cannot be empty")
                    
                    with col_reset:
                        if st.button("↺ Reset", use_container_width=True):
                            # Show warning instead of directly modifying
                            st.warning("⚠️ Reset will restore default prompt. Save current changes first!")
                            if st.button("✅ Confirm Reset", key="confirm_reset_sidebar"):
                                from ragflow_assistant_manager import create_default_assistant_config
                                default_config = create_default_assistant_config()
                                # Reset the assistant prompt directly without session state
                                success = st.session_state.session_manager.assistant_manager.update_prompt(default_config.system_prompt)
                                if success:
                                    st.session_state.session_manager.assistant_config.system_prompt = default_config.system_prompt
                                    st.success("✅ Reset to default!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("❌ Reset failed")
                    
                    with col_health:
                        if st.button("🔍 Health", use_container_width=True):
                            with st.spinner("Checking..."):
                                health = st.session_state.session_manager.assistant_manager.health_check()
                                if all(health.values()):
                                    st.success("✅ OK")
                                else:
                                    st.warning("⚠️ Issues")
            
            # Show helpful message if nothing is enabled
            if (os.getenv("SHOW_CONFIG_METRICS", "false").lower() == "false" and 
                os.getenv("SHOW_PROMPT_EDITOR", "false").lower() == "false"):
                st.info("💡 Enable specific debug features in .env file:\n- SHOW_CONFIG_METRICS=true\n- SHOW_PROMPT_EDITOR=true")
    
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
        page_title="RCSB PDB ChatBot",
        page_icon="🧬",
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
        
    
    # Main interface
    display_main_interface()
    


if __name__ == "__main__":
    main()