#!/usr/bin/env python3
"""
RAGFlow Assistant Manager
Intelligent management of RAGFlow chat assistants with automated creation, configuration, and session management.
"""

import os
import time
from typing import Dict, List, Optional, Any, Generator
from dataclasses import dataclass
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from ragflow_sdk import RAGFlow
except ImportError:
    raise ImportError("RAGFlow SDK not installed. Run: pip install ragflow-sdk")


@dataclass
class AssistantConfig:
    """Configuration for RAGFlow chat assistant"""
    name: str
    dataset_name: str = "rcsb_pdb_knowledge_base"
    system_prompt: str = ""
    model_name: str = "gpt-4.1"
    temperature: float = 0.1
    top_p: float = 0.3
    presence_penalty: float = 0.2
    frequency_penalty: float = 0.7
    similarity_threshold: float = 0.2
    keywords_similarity_weight: float = 0.7
    top_n: int = 8
    top_k: int = 1024
    opener: str = "Hi! I'm your RCSB PDB assistant. I can help you with protein structures, crystallography, and structural biology questions. What would you like to know?"
    show_quote: bool = True


@dataclass
class StreamingResponse:
    """Represents a streaming response from RAGFlow"""
    content: str
    references: Optional[List[Dict]] = None
    is_complete: bool = False


class RAGFlowAssistantManager:
    """Smart manager for RAGFlow chat assistants with automated lifecycle management"""

    def __init__(self, api_key: str, base_url: str):
        """
        Initialize the RAGFlow assistant manager

        Args:
            api_key: RAGFlow API key
            base_url: RAGFlow server base URL
        """
        self.api_key = api_key
        self.base_url = base_url
        self._ragflow_client = None
        self._current_assistant = None
        self._dataset_cache = {}

    @property
    def ragflow_client(self):
        """Lazy initialization of RAGFlow client"""
        if self._ragflow_client is None:
            self._ragflow_client = RAGFlow(api_key=self.api_key, base_url=self.base_url)
        return self._ragflow_client

    def get_or_create_dataset(self, dataset_name: str) -> str:
        """
        Get existing dataset or create if it doesn't exist

        Args:
            dataset_name: Name of the dataset

        Returns:
            Dataset ID
        """
        # Check cache first
        if dataset_name in self._dataset_cache:
            return self._dataset_cache[dataset_name]

        try:
            # Try to find existing dataset
            datasets = self.ragflow_client.list_datasets(name=dataset_name)
            if datasets:
                dataset_id = datasets[0].id
                self._dataset_cache[dataset_name] = dataset_id
                print(f"✅ Found existing dataset: {dataset_name} (ID: {dataset_id})")
                return dataset_id
        except Exception as e:
            print(f"⚠️  Error searching for dataset {dataset_name}: {e}")

        # Create new dataset if not found
        try:
            from ragflow_sdk import DataSet

            # Configure for scientific documents with RAPTOR
            parser_config = DataSet.ParserConfig(
                chunk_token_num=512,
                delimiter="\\n",
                html4excel=False,
                layout_recognize="DeepDOC",
                raptor={"use_raptor": True}
            )

            dataset = self.ragflow_client.create_dataset(
                name=dataset_name,
                description="RCSB PDB knowledge base with scientific documentation",
                embedding_model="text-embedding-3-large@OpenAI",
                chunk_method="naive",
                parser_config=parser_config
            )

            dataset_id = dataset.id
            self._dataset_cache[dataset_name] = dataset_id
            print(f"🆕 Created new dataset: {dataset_name} (ID: {dataset_id})")
            return dataset_id

        except Exception as e:
            print(f"❌ Error creating dataset {dataset_name}: {e}")
            raise

    def get_or_create_assistant(self, config: AssistantConfig) -> str:
        """
        Get existing chat assistant or create if it doesn't exist

        Args:
            config: Assistant configuration

        Returns:
            Chat assistant ID
        """
        try:
            # Try to find existing assistant
            assistants = self.ragflow_client.list_chats(name=config.name)
            if assistants:
                assistant = assistants[0]

                # Update configuration if needed
                self._update_assistant_config(assistant, config)

                self._current_assistant = assistant
                print(f"✅ Using existing assistant: {config.name} (ID: {assistant.id})")
                return assistant.id

        except Exception as e:
            print(f"⚠️  Error searching for assistant {config.name}: {e}")

        # Create new assistant
        try:
            # Get dataset ID
            dataset_id = self.get_or_create_dataset(config.dataset_name)

            # Create assistant with default LLM settings
            assistant = self.ragflow_client.create_chat(
                name=config.name,
                dataset_ids=[dataset_id],
                llm=None,  # Use default LLM settings
                prompt=None  # Use default prompt settings
            )

            # Update assistant with custom configuration
            self._update_assistant_config(assistant, config)

            self._current_assistant = assistant
            print(f"🆕 Created new assistant: {config.name} (ID: {assistant.id})")
            return assistant.id

        except Exception as e:
            print(f"❌ Error creating assistant {config.name}: {e}")
            raise

    def _update_assistant_config(self, assistant, config: AssistantConfig):
        """
        Update assistant configuration if needed

        Args:
            assistant: RAGFlow Chat object
            config: New configuration
        """
        try:
            # Get dataset ID
            dataset_id = self.get_or_create_dataset(config.dataset_name)

            # Prepare update payload with proper structure
            update_data = {
                "name": config.name,
                "dataset_ids": [dataset_id],
                "prompt": {
                    "similarity_threshold": config.similarity_threshold,
                    "keywords_similarity_weight": config.keywords_similarity_weight,
                    "top_n": config.top_n,
                    "top_k": config.top_k,
                    "variables": [{"key": "knowledge", "optional": True}],
                    "opener": config.opener,
                    "show_quote": config.show_quote,
                    "prompt": config.system_prompt
                }
            }

            # Update assistant
            assistant.update(update_data)
            print(f"🔄 Updated assistant configuration: {config.name}")

        except Exception as e:
            print(f"⚠️  Error updating assistant config: {e}")

    def create_session(self, assistant_id: str, session_name: str = "New Session") -> str:
        """
        Create a new chat session

        Args:
            assistant_id: ID of the chat assistant
            session_name: Name for the session

        Returns:
            Session ID
        """
        try:
            # Get assistant if not cached
            if not self._current_assistant or self._current_assistant.id != assistant_id:
                assistants = self.ragflow_client.list_chats(id=assistant_id)
                if not assistants:
                    raise ValueError(f"Assistant {assistant_id} not found")
                self._current_assistant = assistants[0]

            # Create session
            session = self._current_assistant.create_session(name=session_name)
            print(f"🆕 Created session: {session_name} (ID: {session.id})")
            return session.id

        except Exception as e:
            print(f"❌ Error creating session: {e}")
            raise

    def send_message(self, session_id: str, message: str, stream: bool = True) -> Generator[StreamingResponse, None, None]:
        """
        Send message to chat session and get streaming response

        Args:
            session_id: Session ID
            message: User message
            stream: Whether to stream response

        Yields:
            StreamingResponse objects
        """
        try:
            # Find session
            if not self._current_assistant:
                raise ValueError("No current assistant available")

            sessions = self._current_assistant.list_sessions(id=session_id)
            if not sessions:
                raise ValueError(f"Session {session_id} not found")

            session = sessions[0]

            if stream:
                # Stream response
                full_content = ""
                references = []

                for response in session.ask(message, stream=True):
                    if response.content:
                        full_content = response.content

                        yield StreamingResponse(
                            content=full_content,
                            references=getattr(response, 'reference', None),
                            is_complete=False
                        )

                # Final response
                yield StreamingResponse(
                    content=full_content,
                    references=getattr(response, 'reference', None) if 'response' in locals() else None,
                    is_complete=True
                )

            else:
                # Non-streaming response
                response = session.ask(message, stream=False)
                yield StreamingResponse(
                    content=response.content,
                    references=getattr(response, 'reference', None),
                    is_complete=True
                )

        except Exception as e:
            print(f"❌ Error sending message: {e}")
            yield StreamingResponse(
                content=f"Error: {str(e)}",
                references=None,
                is_complete=True
            )

    def list_assistants(self) -> List[Dict]:
        """List all available chat assistants"""
        try:
            assistants = self.ragflow_client.list_chats()
            return [
                {
                    "id": assistant.id,
                    "name": assistant.name,
                    "created_at": getattr(assistant, 'create_time', 'Unknown')
                }
                for assistant in assistants
            ]
        except Exception as e:
            print(f"❌ Error listing assistants: {e}")
            return []

    def delete_assistant(self, assistant_id: str):
        """Delete a chat assistant"""
        try:
            self.ragflow_client.delete_chats(ids=[assistant_id])
            print(f"🗑️ Deleted assistant: {assistant_id}")
        except Exception as e:
            print(f"❌ Error deleting assistant: {e}")
            raise

    def health_check(self) -> Dict[str, bool]:
        """Check health of RAGFlow connection and services"""
        health_status = {
            "ragflow_connection": False,
            "dataset_access": False,
            "assistant_access": False
        }

        try:
            # Test basic connection
            datasets = self.ragflow_client.list_datasets(page=1, page_size=1)
            health_status["ragflow_connection"] = True
            health_status["dataset_access"] = True

            # Test assistant access
            assistants = self.ragflow_client.list_chats(page=1, page_size=1)
            health_status["assistant_access"] = True

        except Exception as e:
            print(f"⚠️  Health check failed: {e}")

        return health_status
    
    def update_prompt(self, new_prompt: str) -> bool:
        """
        Update the system prompt for the current assistant
        
        Args:
            new_prompt: New system prompt content
            
        Returns:
            True if successful, False otherwise
        """
        if not self._current_assistant:
            print("❌ No current assistant available for prompt update")
            return False
        
        try:
            # Get dataset ID for the current assistant's configuration
            dataset_id = None
            if hasattr(self._current_assistant, 'dataset_ids') and self._current_assistant.dataset_ids:
                dataset_id = self._current_assistant.dataset_ids[0]
            else:
                # Fallback: get default dataset
                dataset_id = self.get_or_create_dataset("rcsb_pdb_knowledge_base")
            
            # Prepare update payload with new prompt
            update_data = {
                "prompt": {
                    "prompt": new_prompt,
                    "variables": [{"key": "knowledge", "optional": True}],
                    "show_quote": True
                }
            }
            
            # Update assistant prompt
            self._current_assistant.update(update_data)
            print(f"✅ Updated assistant prompt successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error updating assistant prompt: {e}")
            return False


def create_assistant_manager() -> RAGFlowAssistantManager:
    """Create and configure RAGFlow assistant manager from environment variables"""

    # Get required configuration
    api_key = os.getenv("RAGFLOW_API_KEY")
    base_url = os.getenv("RAGFLOW_BASE_URL", "http://127.0.0.1:9380")

    if not api_key:
        raise ValueError("RAGFLOW_API_KEY environment variable is required")

    return RAGFlowAssistantManager(api_key=api_key, base_url=base_url)


def create_default_assistant_config() -> AssistantConfig:
    """Create default assistant configuration from environment variables"""

    # Default enhanced knowledge base prompt
    default_prompt = """# Enhanced Knowledge Base Assistant Prompt

You are a knowledge base assistant with **STRICT BOUNDARIES**. Your role is to provide information **EXCLUSIVELY** from the provided knowledge base. You must never use external knowledge, make assumptions, or provide information not explicitly contained in the knowledge base.

## Core Instructions:

### STRICT COMPLIANCE RULES:
1. **ONLY answer using information explicitly present in the knowledge base below**
2. **NEVER supplement with external knowledge, even if you know the answer**
3. **NEVER make inferences or assumptions beyond what is directly stated**
4. **NEVER provide partial answers using external knowledge**
5. **ALWAYS cite specific sections/sources from the knowledge base when answering**

### MANDATORY RESPONSE PROTOCOL:
- **If the knowledge base contains relevant information**: Provide a comprehensive answer using ONLY that information
- **If the knowledge base contains partial information**: Answer only what is available and state what information is missing
- **If the knowledge base contains NO relevant information**: You MUST include this exact sentence: **"The answer you are looking for is not found in the knowledge base!"**

### KNOWLEDGE BASE CONTENT:
{knowledge}
**END OF KNOWLEDGE BASE**

---

## Response Requirements:

### CRITICAL FORMATTING RULE:
**ALL responses must be wrapped in a single ```markdown code block with NOTHING outside the block.**

### Response Format Template:
```markdown
## [Response Title]

[Your comprehensive answer here using ONLY knowledge base information]

### Key Points:
- Point 1 from knowledge base
- Point 2 from knowledge base

### References:
Available reference IDs: [ID:1] [ID:2] [ID:3] [ID:4]

[If no relevant information exists, include: "The answer you are looking for is not found in the knowledge base!"]
```

Content Guidelines:

- Primary Rule: Extract and summarize ONLY information present in the above knowledge base
- Transparency: Ensure all information comes directly from the knowledge base
- Completeness: List all relevant data points from the knowledge base related to the question
- Context Awareness: Consider previous chat history when formulating responses
- Accuracy: Quote or paraphrase directly from the knowledge base - no interpretation or expansion
- Reference Integration: Include reference markers [ID:X] WITHIN the markdown block in a References section

Formatting Standards:

- Use markdown formatting with proper headings, lists, and code blocks
- Structure answers with clear sections (## Overview, ## Methods, ## Steps, etc.)
- Include specific examples, commands, and URLs exactly as they appear in the knowledge base
- Use bullet points and numbered lists for procedures
- Format code/commands in code blocks and inline code
- Bold important terms and key information
- Use tables when appropriate for structured data
- CRITICAL: Keep ALL content including reference markers inside the ```markdown block

Quality Assurance Checklist:

Before responding, verify:
- Is every piece of information in my response found in the knowledge base?
- Have I included the mandatory sentence if no relevant information exists?
- Am I using proper markdown formatting?
- Have I considered the chat history context?
- Are ALL reference markers [ID:X] included WITHIN the ```markdown block?
- Is there NOTHING outside the ```markdown code block?

---
FINAL REMINDER:
1. You are a knowledge base assistant, NOT a general AI assistant
2. Your knowledge is limited EXCLUSIVELY to the content provided above
3. EVERYTHING must be inside the ```markdown block - NO exceptions
4. Reference markers [ID:X] belong in a "References" section WITHIN the markdown block"""

    return AssistantConfig(
        name=os.getenv("RAGFLOW_ASSISTANT_NAME", "RCSB ChatBot v2"),
        dataset_name=os.getenv("RAGFLOW_DATASET_NAME", "rcsb_pdb_knowledge_base"),
        system_prompt=os.getenv("RAGFLOW_SYSTEM_PROMPT", default_prompt),
        model_name=os.getenv("RAGFLOW_MODEL_NAME", "gpt-4.1"),
        temperature=float(os.getenv("RAGFLOW_TEMPERATURE", "0.1")),
        top_p=float(os.getenv("RAGFLOW_TOP_P", "0.3")),
        presence_penalty=float(os.getenv("RAGFLOW_PRESENCE_PENALTY", "0.2")),
        frequency_penalty=float(os.getenv("RAGFLOW_FREQUENCY_PENALTY", "0.7")),
        similarity_threshold=float(os.getenv("RAGFLOW_SIMILARITY_THRESHOLD", "0.2")),
        keywords_similarity_weight=float(os.getenv("RAGFLOW_KEYWORDS_WEIGHT", "0.7")),
        top_n=int(os.getenv("RAGFLOW_TOP_N", "8")),
        top_k=int(os.getenv("RAGFLOW_TOP_K", "1024")),
        opener=os.getenv("RAGFLOW_OPENER", "Hi! I'm your RCSB PDB assistant. I can help you with protein structures, crystallography, and structural biology questions. What would you like to know?"),
        show_quote=os.getenv("RAGFLOW_SHOW_QUOTE", "true").lower() == "true"
    )


if __name__ == "__main__":
    # Test the assistant manager
    try:
        print("🧪 Testing RAGFlow Assistant Manager...")

        # Create manager
        manager = create_assistant_manager()
        config = create_default_assistant_config()

        # Health check
        health = manager.health_check()
        print(f"Health Status: {health}")

        # Get or create assistant
        assistant_id = manager.get_or_create_assistant(config)
        print(f"Assistant ID: {assistant_id}")

        # Create session
        session_id = manager.create_session(assistant_id, "Test Session")
        print(f"Session ID: {session_id}")

        # Test message
        print("\n🤖 Testing message...")
        for response in manager.send_message(session_id, "Hello, what can you help me with?"):
            if response.is_complete:
                print(f"Response: {response.content[:100]}...")
                break

        print("✅ All tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")