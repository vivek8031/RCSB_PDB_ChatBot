# RAGFlow Python SDK Reference (v0.20.4)

Complete API reference for RAGFlow Python SDK integration.

## Overview

The RAGFlow Python SDK provides a comprehensive API for interacting with RAGFlow's AI-powered document and chat management system. This SDK enables developers to build applications that can:

- Manage datasets and documents
- Create and configure chat assistants
- **NEW**: Create and manage intelligent agents
- Handle conversational AI interactions
- Process and chunk documents
- Manage user sessions and conversations

**What's New in v0.20.4:**
- Agent management system for more flexible AI interactions
- Enhanced session handling for both assistants and agents
- Improved configuration options and error handling

## Installation & Setup

### Installation
```bash
pip install ragflow-sdk
```

### Basic Configuration
```python
from ragflow_sdk import RAGFlow

# Initialize the RAGFlow client
rag_client = RAGFlow(
    api_key="<YOUR_API_KEY>", 
    base_url="http://<YOUR_BASE_URL>:9380"
)
```

### Environment Variables
```bash
RAGFLOW_API_KEY=your-api-key-here
RAGFLOW_BASE_URL=http://127.0.0.1:9380
```

## Core Classes and Methods

### 1. RAGFlow Client Class

#### Constructor
```python
RAGFlow(api_key: str, base_url: str)
```
- **api_key**: Your RAGFlow API authentication key
- **base_url**: Base URL of your RAGFlow instance (e.g., "http://localhost:9380")

#### Key Methods

##### Dataset Operations
```python
# Create a new dataset
create_dataset(
    name: str,
    chunk_method: str = "naive",  # Options: "naive", "manual", "qa"
    permission: str = "me"        # Options: "me", "team"
) -> Dataset

# List all datasets
list_datasets(
    page: int = 1,
    page_size: int = 30,
    orderby: str = "create_time"  # Options: "create_time", "update_time"
) -> List[Dataset]

# Get specific dataset
get_dataset(dataset_id: str) -> Dataset

# Delete dataset
delete_dataset(dataset_id: str) -> bool
```

##### Chat Assistant Operations
```python
# Create chat assistant
create_chat(
    name: str,
    dataset_ids: List[str],
    llm: dict = None,
    prompt: dict = None
) -> Assistant

# List chat assistants
list_chats(
    page: int = 1,
    page_size: int = 30
) -> List[Assistant]

# Get specific assistant
get_chat(assistant_id: str) -> Assistant

# Delete assistant
delete_chat(assistant_id: str) -> bool
```

##### Agent Operations (New in v0.20.4)
```python
# Create agent
create_agent(
    name: str,
    description: str = "",
    llm: dict = None,
    prompt: dict = None
) -> Agent

# List agents
list_agents(
    page: int = 1,
    page_size: int = 30
) -> List[Agent]

# Get specific agent
get_agent(agent_id: str) -> Agent

# Update agent
update_agent(
    agent_id: str,
    name: str = None,
    description: str = None,
    llm: dict = None,
    prompt: dict = None
) -> bool

# Delete agent
delete_agent(agent_id: str) -> bool
```

### 2. Dataset Class

#### Properties
- `id`: Dataset unique identifier
- `name`: Dataset name
- `chunk_method`: Chunking strategy used
- `document_count`: Number of documents in dataset
- `chunk_count`: Number of chunks generated

#### Methods
```python
# Upload documents to dataset
upload_documents(documents: List[dict]) -> List[Document]
# documents format: [{"display_name": "file.txt", "blob": file_content}]

# List documents in dataset
list_documents(
    keywords: str = "",
    page: int = 1,
    page_size: int = 30
) -> List[Document]

# Delete document from dataset
delete_document(document_id: str) -> bool

# Update dataset configuration
update(
    name: str = None,
    chunk_method: str = None
) -> bool
```

### 3. Document Class

#### Properties
- `id`: Document unique identifier
- `name`: Display name of document
- `size`: File size in bytes
- `type`: Document type (pdf, txt, docx, etc.)
- `chunk_count`: Number of chunks generated
- `status`: Processing status

#### Methods
```python
# Get document chunks
list_chunks(
    keywords: str = "",
    page: int = 1,
    page_size: int = 30
) -> List[Chunk]

# Update document
update(name: str = None) -> bool

# Delete document
delete() -> bool
```

### 4. Assistant Class

#### Properties
- `id`: Assistant unique identifier
- `name`: Assistant name
- `dataset_ids`: Associated dataset IDs
- `llm_setting`: Language model configuration
- `prompt_config`: Prompt template configuration

#### Methods
```python
# Create new conversation session
create_session() -> Session

# List existing sessions
list_sessions(
    page: int = 1,
    page_size: int = 30
) -> List[Session]

# Update assistant configuration
update(
    name: str = None,
    dataset_ids: List[str] = None,
    llm: dict = None,
    prompt: dict = None
) -> bool

# Delete assistant
delete() -> bool
```

### 5. Agent Class (New in v0.20.4)

#### Properties
- `id`: Agent unique identifier
- `name`: Agent name
- `description`: Agent description
- `llm_setting`: Language model configuration
- `prompt_config`: Prompt template configuration

#### Methods
```python
# Create new agent session
create_session() -> Session

# List existing agent sessions
list_sessions(
    page: int = 1,
    page_size: int = 30
) -> List[Session]

# Update agent configuration
update(
    name: str = None,
    description: str = None,
    llm: dict = None,
    prompt: dict = None
) -> bool

# Delete agent
delete() -> bool
```

### 6. Session Class

#### Properties
- `id`: Session unique identifier
- `name`: Session name
- `assistant_id`: Associated assistant ID (or agent_id for agent sessions)
- `message_count`: Number of messages in session

#### Methods
```python
# Ask question with streaming response
ask(
    question: str,
    stream: bool = True,
    **kwargs
) -> Generator[dict, None, None] or dict

# List conversation messages
list_messages(
    page: int = 1,
    page_size: int = 30
) -> List[Message]

# Update session
update(name: str = None) -> bool

# Delete session
delete() -> bool
```

## Configuration Options

### LLM Configuration
```python
llm_config = {
    "model_name": "default",        # Model to use
    "temperature": 0.1,             # Response randomness (0.0-2.0)
    "top_p": 0.95,                  # Nucleus sampling
    "max_tokens": 2048,             # Maximum response length
    "presence_penalty": 0.0,        # Repetition penalty
    "frequency_penalty": 0.0        # Frequency penalty
}
```

### Prompt Configuration
```python
prompt_config = {
    "system": "You are a helpful assistant.",
    "quote": True,                  # Include source quotes
    "empty_response": "I don't know based on the provided context.",
    "keywords_similarity_weight": 0.7,
    "top_n_similarity": 6
}
```

### Chunk Methods
- **"naive"**: Simple text splitting
- **"manual"**: User-defined chunks  
- **"qa"**: Question-answer based chunking

## Usage Examples

### Complete Workflow Example (Assistant-based)
```python
from ragflow_sdk import RAGFlow

# Initialize client
rag = RAGFlow(api_key="your-key", base_url="http://localhost:9380")

# Create dataset
dataset = rag.create_dataset(name="my_knowledge_base")

# Upload documents
with open("document.pdf", "rb") as f:
    dataset.upload_documents([{
        "display_name": "document.pdf",
        "blob": f.read()
    }])

# Create assistant
assistant = rag.create_chat(
    name="My Assistant",
    dataset_ids=[dataset.id],
    llm={"temperature": 0.1}
)

# Start conversation
session = assistant.create_session()

# Ask questions with streaming
for chunk in session.ask("What is this document about?"):
    if chunk.get("retcode") == 0:
        answer = chunk.get("data", {}).get("answer", "")
        print(answer, end="", flush=True)
```

### Agent-based Workflow Example (New)
```python
from ragflow_sdk import RAGFlow

# Initialize client
rag = RAGFlow(api_key="your-key", base_url="http://localhost:9380")

# Create agent (more flexible than assistants)
agent = rag.create_agent(
    name="Research Agent",
    description="Specialized in research tasks",
    llm={"temperature": 0.2, "model_name": "gpt-4"}
)

# Start agent session
session = agent.create_session()

# Interact with agent
for chunk in session.ask("Help me analyze this research paper"):
    if chunk.get("retcode") == 0:
        answer = chunk.get("data", {}).get("answer", "")
        print(answer, end="", flush=True)

# Agents can be updated dynamically
agent.update(
    description="Updated to handle complex analysis",
    llm={"temperature": 0.1}
)
```

### Error Handling
```python
try:
    dataset = rag.create_dataset(name="test")
    documents = dataset.upload_documents([{
        "display_name": "test.txt",
        "blob": b"Hello world"
    }])
except Exception as e:
    print(f"Error: {e}")
    # Handle specific error types
    if "authentication" in str(e).lower():
        print("Check your API key")
    elif "network" in str(e).lower():
        print("Check your base URL and connectivity")
```

### Session Management
```python
# Create named session
session = assistant.create_session()

# Continue conversation
response1 = session.ask("What is machine learning?")
response2 = session.ask("Can you give me more details about neural networks?")

# List conversation history
messages = session.list_messages()
for message in messages:
    print(f"{message.role}: {message.content}")
```

## Best Practices

### 1. Connection Management
```python
# Reuse client instance
rag_client = RAGFlow(api_key=API_KEY, base_url=BASE_URL)

# Use context managers for file handling
with open("document.pdf", "rb") as f:
    content = f.read()
```

### 2. Error Handling
```python
# Always wrap API calls in try-except
try:
    result = rag_client.create_dataset("name")
except Exception as e:
    logging.error(f"Failed to create dataset: {e}")
```

### 3. Resource Management
```python
# Clean up unused resources
if not dataset_needed:
    dataset.delete()

# Limit session count
sessions = assistant.list_sessions()
if len(sessions) > 10:
    oldest_session = sessions[-1]
    oldest_session.delete()
```

### 4. Configuration
```python
# Use environment variables
import os
rag = RAGFlow(
    api_key=os.getenv("RAGFLOW_API_KEY"),
    base_url=os.getenv("RAGFLOW_BASE_URL", "http://localhost:9380")
)
```

## Response Format

### Streaming Response Structure
```python
{
    "retcode": 0,                    # Status code (0 = success)
    "retmsg": "success",             # Status message
    "data": {
        "answer": "response text",   # AI response
        "reference": [{              # Source references
            "chunk_id": "chunk_123",
            "content": "source text",
            "document_id": "doc_456",
            "document_name": "file.pdf",
            "similarity": 0.85
        }],
        "session_id": "session_789"
    }
}
```

### Error Response Structure  
```python
{
    "retcode": 1,                    # Non-zero indicates error
    "retmsg": "Error description",   # Error details
    "data": None
}
```

## Integration Notes

### For RCSB PDB ChatBot
The current implementation uses:
- **Dataset**: RCSB PDB knowledge base
- **Assistant**: "RCSB ChatBot v2" 
- **Sessions**: User-specific with unique IDs
- **Streaming**: Real-time response display

**Potential Agent Integration:**
- Agents could provide more specialized responses for different research areas
- Dynamic agent updating for different protein structure tasks
- Multiple agents for different expertise areas (crystallography, NMR, etc.)

### Version Compatibility
- **SDK Version**: 0.19.0+
- **RAGFlow Server**: v0.20.4+
- **Python**: 3.8+

## Troubleshooting

### Common Issues
1. **Authentication Error**: Check API key validity
2. **Connection Error**: Verify base URL and network connectivity
3. **Document Upload**: Ensure file format is supported
4. **Session Timeout**: Handle expired sessions gracefully

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# SDK will now output detailed logs
```