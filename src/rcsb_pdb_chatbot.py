#!/usr/bin/env python3
"""
RCSB PDB Help Desk - Anonymous Chatbot for Structural Biology
A minimal, user-friendly Streamlit interface for protein structure queries
"""

import streamlit as st
import time
import os
import re
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from user_session_manager import UserSessionManager, UserChat, create_manager


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


def init_session_state():
    """Initialize Streamlit session state variables"""
    if "session_manager" not in st.session_state:
        st.session_state.session_manager = create_manager()

    if "browser_session_id" not in st.session_state:
        st.session_state.browser_session_id = None

    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = None

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "show_references" not in st.session_state:
        st.session_state.show_references = True


def init_anonymous_session():
    """Initialize anonymous session with auto-generated UUID"""

    # Check for existing session in query params
    if "sid" in st.query_params:
        browser_session_id = st.query_params["sid"]
    else:
        # Generate new UUID
        browser_session_id = str(uuid.uuid4())
        st.query_params["sid"] = browser_session_id

    st.session_state.browser_session_id = browser_session_id

    # Auto-create chat if none exists
    if not st.session_state.current_chat_id:
        existing_chats = st.session_state.session_manager.list_user_chats(browser_session_id)

        if existing_chats:
            # Resume most recent chat
            st.session_state.current_chat_id = existing_chats[-1].chat_id
        else:
            # Create first chat
            chat_title = f"Help Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            new_chat = st.session_state.session_manager.create_user_chat(
                browser_session_id,
                chat_title
            )
            st.session_state.current_chat_id = new_chat.chat_id

        load_chat_messages()


def load_chat_messages():
    """Load stored messages for the current chat"""
    if not st.session_state.browser_session_id or not st.session_state.current_chat_id:
        st.session_state.messages = []
        return

    try:
        # Get stored messages from the session manager
        stored_messages = st.session_state.session_manager.get_chat_messages(
            st.session_state.browser_session_id,
            st.session_state.current_chat_id
        )

        # Convert StoredMessage objects to Streamlit message format
        st.session_state.messages = []
        for stored_msg in stored_messages:
            message_dict = {
                "role": stored_msg.role,
                "content": stored_msg.content,
                "timestamp": stored_msg.timestamp.isoformat(),
                "message_id": stored_msg.message_id
            }

            # Add references if available
            if stored_msg.references:
                message_dict["references"] = stored_msg.references

            st.session_state.messages.append(message_dict)

        print(f"Loaded {len(st.session_state.messages)} messages for chat {st.session_state.current_chat_id}")

    except Exception as e:
        print(f"Error loading chat messages: {e}")
        st.session_state.messages = []


def start_new_chat():
    """Start a fresh conversation"""
    chat_title = f"Help Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    new_chat = st.session_state.session_manager.create_user_chat(
        st.session_state.browser_session_id,
        chat_title
    )
    st.session_state.current_chat_id = new_chat.chat_id
    st.session_state.messages = []


def display_header():
    """Display minimal header with New Chat button"""
    # Custom CSS for header styling
    st.markdown("""
    <style>
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem 0;
        border-bottom: 1px solid #e0e0e0;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([6, 1])

    with col1:
        st.markdown("### RCSB PDB")

    with col2:
        if st.button("New Chat", type="primary", use_container_width=True, help="Start a new conversation"):
            start_new_chat()
            st.rerun()

    st.divider()


def display_star_rating(message: Dict[str, Any]):
    """
    Display inline 1-5 star rating under assistant message

    Args:
        message: Message dictionary containing role, content, message_id, etc.
    """
    if message["role"] != "assistant":
        return

    message_id = message.get("message_id")
    if not message_id:
        return

    # Get existing feedback
    existing_feedback = None
    if (st.session_state.browser_session_id and
        st.session_state.current_chat_id and
        hasattr(st.session_state, 'session_manager')):
        existing_feedback = st.session_state.session_manager.get_message_feedback(
            st.session_state.browser_session_id,
            st.session_state.current_chat_id,
            message_id
        )

    existing_rating = None
    if existing_feedback:
        existing_rating = existing_feedback.get("star_rating")

    # Display star rating widget
    col1, col2 = st.columns([3, 1])

    with col1:
        # st.feedback("stars") returns 0-4 for 5 stars
        star_value = st.feedback(
            "stars",
            key=f"stars_{message_id}"
        )

        # Convert 0-4 to 1-5 and save if selected
        if star_value is not None:
            new_rating = star_value + 1  # Convert 0-4 to 1-5

            # Only save if rating changed
            if existing_rating != new_rating:
                feedback_data = {
                    "star_rating": new_rating,
                    "feedback_timestamp": datetime.now().isoformat()
                }
                st.session_state.session_manager.add_message_feedback(
                    st.session_state.browser_session_id,
                    st.session_state.current_chat_id,
                    message_id,
                    feedback_data
                )

    with col2:
        if existing_rating:
            st.caption(f"Rated: {existing_rating}/5")


def display_chat_interface():
    """Display the main chat interface"""

    # Get current chat info for context
    current_chat = None
    if st.session_state.current_chat_id:
        current_chat = st.session_state.session_manager.get_user_chat(
            st.session_state.browser_session_id,
            st.session_state.current_chat_id
        )

    # Display welcome message if no messages yet
    if not st.session_state.messages:
        st.markdown("""
        ### Welcome to RCSB PDB

        Ask me anything about:
        - **Protein Data Bank (PDB)** structures and entries
        - **Crystallography** and structure determination methods
        - **Molecular biology** and protein science concepts
        - **Structure deposition** and validation processes
        - **wwPDB policies** and procedures

        Just type your question below to get started!
        """)

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            # Process and render markdown content
            processed_content = process_markdown_response(message["content"])
            st.markdown(processed_content)

            # Show references if available
            if (message["role"] == "assistant" and
                st.session_state.show_references and
                message.get("references")):

                with st.expander("References"):
                    for i, ref in enumerate(message["references"], 1):
                        st.markdown(f"**Reference {i}: {ref.get('document_name', 'Unknown')}**")
                        st.caption(f"Similarity Score: {ref.get('similarity', 0):.2f}")

                        ref_content = ref.get('content', '')
                        if ref_content:
                            with st.container():
                                st.markdown("**Content:**")
                                st.markdown(ref_content, unsafe_allow_html=False)

                        if i < len(message["references"]):
                            st.divider()

            # Add star rating for assistant messages
            if message["role"] == "assistant":
                display_star_rating(message)

    # Chat input
    if prompt := st.chat_input("Ask about RCSB PDB, protein structures, or anything related..."):
        # Add user message to chat history
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat()
        })

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
                assistant_message_id = None
                for response_chunk in st.session_state.session_manager.send_message_to_chat(
                    st.session_state.browser_session_id,
                    st.session_state.current_chat_id,
                    prompt
                ):
                    # Update the message as it streams
                    if response_chunk.content != full_response:
                        full_response = response_chunk.content
                        processed_content = process_markdown_response(full_response)
                        message_placeholder.markdown(processed_content)

                    # Capture references and message ID from the final response
                    if response_chunk.references:
                        references = response_chunk.references
                    if response_chunk.message_id:
                        assistant_message_id = response_chunk.message_id

                # Add assistant message to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_response,
                    "references": references,
                    "message_id": assistant_message_id,
                    "timestamp": datetime.now().isoformat()
                })

                # Show references if available
                if st.session_state.show_references and references:
                    with st.expander("References"):
                        for i, ref in enumerate(references, 1):
                            st.markdown(f"**Reference {i}: {ref.get('document_name', 'Unknown')}**")
                            st.caption(f"Similarity Score: {ref.get('similarity', 0):.2f}")

                            ref_content = ref.get('content', '')
                            if ref_content:
                                with st.container():
                                    st.markdown("**Content:**")
                                    st.markdown(ref_content, unsafe_allow_html=False)

                            if i < len(references):
                                st.divider()

                # Add star rating for the new response
                if full_response:
                    new_message = {
                        "role": "assistant",
                        "content": full_response,
                        "references": references,
                        "message_id": assistant_message_id,
                        "timestamp": datetime.now().isoformat()
                    }
                    display_star_rating(new_message)

            except Exception as e:
                st.error(f"Error getting response: {e}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Sorry, I encountered an error: {e}",
                    "message_id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat()
                })


def main():
    """Main application function - Anonymous Help Desk"""
    # Page configuration
    st.set_page_config(
        page_title="RCSB PDB",
        page_icon="",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # Hide sidebar completely with CSS
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stSidebarNav"] { display: none; }
    .main > div {
        padding-top: 1rem;
        max-width: 900px;
        margin: 0 auto;
    }
    /* Mobile responsive adjustments */
    @media (max-width: 768px) {
        .main > div {
            padding: 0.5rem;
        }
    }
    /* Star rating touch targets */
    [data-testid="stFeedback"] button {
        min-height: 44px;
        min-width: 44px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Initialize session state
    init_session_state()

    # Initialize anonymous session (auto UUID + auto chat)
    init_anonymous_session()

    # Display header with New Chat button
    display_header()

    # Display chat interface
    display_chat_interface()


if __name__ == "__main__":
    main()
