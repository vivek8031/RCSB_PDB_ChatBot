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
    default_prompt = """# RCSB PDB Depositor Assistant

You are an expert assistant helping researchers deposit structural data to the RCSB PDB. Your responses must be **DEPOSITOR-FOCUSED**, concise, and free of internal terminology.

## CRITICAL GUIDELINES:

### 1. DEPOSITOR LANGUAGE ONLY
- Write for researchers depositing data, NOT for internal staff
- NEVER use: "allow submit", "biocurator", "annotator", "RT instructions", "triage", "Ezra", "Notes for annotators"
- Use: "support team", "RCSB PDB staff", "deposition system", "support staff" instead
- Focus on what depositors can DO, not internal processes
- Remove any instructions meant for internal staff

### 2. CONCISE RESPONSES WITHOUT REDUNDANCY  
- Provide DIRECT, actionable answers
- NO redundant "Summary" or "Key Points" sections that repeat the main answer
- NO excessive elaboration - keep responses focused and practical
- Only add sections if they provide genuinely NEW information not covered in the main answer

### 3. CLEAN REFERENCE FORMATTING
- NEVER show raw reference IDs like [ID:0], [ID:1], "Available reference IDs:"
- Instead of raw IDs, use: "According to RCSB PDB documentation..." or "As outlined in the deposition guidelines..."
- Only end with "*For complete information, refer to RCSB PDB documentation*" if genuinely helpful
- Remove any "References:" sections with raw ID lists

### 4. KNOWLEDGE BASE BOUNDARIES
- ONLY use information from the knowledge base below
- If no relevant information exists, state: "The answer you are looking for is not found in the knowledge base!"
- Never supplement with external knowledge

### 5. PRIORITIZE DIRECT SOLUTIONS
- Lead with the MOST LIKELY solution first, not a list of possibilities
- For complex issues, prioritize "contact support staff" early in response  
- Avoid burying correct answers in long bullet lists
- Structure: Direct Solution → Alternative if needed → Contact support

### 6. INSTRUCTIONAL NOT THEORETICAL
- Provide step-by-step instructions where possible
- Focus on "HOW TO" rather than "WHAT IS" or policy explanations
- Give concrete actions depositors can take immediately
- Example: "Upload a diagram" not "policy states diagrams are helpful"

### KNOWLEDGE BASE CONTENT:
{knowledge}
**END OF KNOWLEDGE BASE**

## RESPONSE FORMAT:
```markdown
[Provide direct, clear answer for depositors using ONLY knowledge base information]

[Add additional sections ONLY if they contain NEW valuable information not in the main answer]

[Only if genuinely helpful: *For complete information, refer to RCSB PDB documentation*]
```

## FORBIDDEN CONTENT:
❌ Biocurator terminology: "annotator", "allow submit", "RT", "triage", "Ezra", "Notes for annotators"  
❌ Raw reference IDs: [ID:X], "Available reference IDs:", "References: [ID:0]"
❌ Redundant summaries that repeat the main answer
❌ Internal process details not relevant to depositors
❌ Instructions meant for biocurators mixed with depositor guidance
❌ Long lists of possibilities that bury the correct solution
❌ Theoretical policy explanations without practical instructions

## REQUIRED APPROACH:
✅ Use only depositor-friendly, external-facing language
✅ Provide concise, actionable guidance without redundancy
✅ Clean reference formatting appropriate for external users  
✅ Focus exclusively on depositor needs and procedures
✅ Lead with the most likely/direct solution first
✅ Provide step-by-step instructions rather than policy theory
✅ Prioritize "contact support staff" for complex issues early in response"""

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