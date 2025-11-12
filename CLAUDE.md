# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **OpenAI Agent with Graphiti Temporal Knowledge Graph Memory** - a conversational AI system that learns and remembers information from past conversations using a temporal knowledge graph stored in Neo4j.

### Key Features
- **Temporal Knowledge Graph**: Uses Graphiti library to store facts with timestamps in Neo4j
- **OpenAI Integration**: Uses standard OpenAI client library with Azure OpenAI backend for LLM responses and embeddings
- **LLM-Controlled Web Search**: Uses OpenAI function calling for intelligent web search decisions
- **Conversation Memory**: Maintains context across multiple turns and learns from past conversations
- **Sync/Async Architecture**: Async processing with sync CLI wrapper for easy use
- **User Isolation**: Maintains separate memory graphs per user using Graphiti's `group_id` parameter
- **Flexible Deployment**: Supports both Azure OpenAI and openai.com endpoints

### Development Status
**Stage**: Active Development (Phase 1-6 in progress)
- Foundation: ✅ Complete (config, basic structures)
- OpenAI Client Conversion: ✅ COMPLETE (from AzureOpenAI to AsyncOpenAI)
- Graphiti Integration: ✅ COMPLETE (with proper embedding_model configuration)
- Neo4j Setup: ✅ Complete and tested
- Function Calling: ✅ Implemented (web search tool)
- Error Handling: ✅ In place
- Testing: ✅ Episode creation, search, and memory retrieval verified

## Technology Stack
- **Python 3.13+**
- **LLM/Embeddings**: OpenAI client library v1.50+ with Azure OpenAI backend
- **Knowledge Graph**: Neo4j 5.26 + Graphiti (temporal KG framework)
- **Web Search**: Tavily API
- **Config**: python-dotenv, Pydantic v2
- **Framework**: Async/await with asyncio
- **Model**: gpt-5-mini-nlq (chat), text-embedding-3-small (embeddings)

## Development Setup

### Prerequisites
- Python 3.13 (use `.python-version` file)
- Docker Desktop (for Neo4j)
- Azure OpenAI credentials
- Tavily API key

### Installation
```bash
# Install dependencies
pip install -e .

# Start Neo4j database
docker-compose up -d neo4j

# Verify Neo4j is running
docker-compose ps
```

### Environment Setup
Create `.env` file with:
```
# OpenAI Configuration (Azure OpenAI v1 API)
OPENAI_API_KEY=<your-azure-openai-api-key>
OPENAI_API_ENDPOINT=https://<resource>.cognitiveservices.azure.com/openai/v1/
OPENAI_CHAT_MODEL=<deployment-name>

# Embedding Configuration (can be different Azure resource)
OPENAI_EMBEDDING_ENDPOINT=https://<resource>.cognitiveservices.azure.com/openai/v1/
OPENAI_EMBEDDING_MODEL=<deployment-name>
OPENAI_EMBEDDING_API_KEY=<optional-separate-key>

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Tavily Search Configuration
TAVILY_API_KEY=<your-tavily-key>

# Agent Configuration
AGENT_NAME=Knowledge Graph Agent
CONVERSATION_HISTORY_LIMIT=10
```

## Running the Application

### CLI Mode
```bash
python main.py
```
Interactive CLI with commands:
- `help` - Show available commands
- `clear` - Clear conversation history
- `exit` or `quit` - Exit the agent

### Code Examples
```python
# Programmatic usage
from src.agent import SyncMemoryAgent

agent = SyncMemoryAgent(user_id="user123")
response = agent.process_message("What did I tell you about Python last week?")
print(response)
agent.close()
```

## Architecture

### Core Components

#### 1. **Agent Layer** (`src/agent.py`)
- `MemoryAgent`: Async core agent
  - Manages conversation flow and message processing
  - Integrates memory retrieval with web search
  - Stores conversation episodes in knowledge graph
  - Maintains conversation history with configurable limits
- `SyncMemoryAgent`: Synchronous wrapper for CLI/blocking usage
  - Wraps async agent with event loop management
  - Provides context manager support

**Key Flow** (with OpenAI function calling):
1. Query memory for relevant context (`get_context_for_query`)
2. Send user message to LLM with available tools (web_search)
3. LLM decides if tool is needed and returns tool calls
4. Execute requested tools (web search via Tavily)
5. Send tool results back to LLM for final response
6. Combine LLM response with memories and return to user
7. Store conversation episode in knowledge graph with `group_id` for user isolation

#### 2. **Memory System** (`src/graphiti_client.py`)
- `GraphitiMemoryClient`: Async wrapper around Graphiti
  - Initializes Graphiti with OpenAI client (AsyncOpenAI) for LLM and embedder
  - Supports separate endpoints for chat and embeddings (different Azure resources)
  - Adds conversation episodes with timestamps
  - Searches knowledge graph with semantic relevance
  - Formats context for agent prompts
- `GraphitiMemory`: Synchronous wrapper for blocking usage
  - Event loop management for sync operations

**Knowledge Graph Storage**:
- Episodes: Individual conversation turns with timestamps
- Nodes/Entities: Automatically extracted by Graphiti from episode content
- Edges: Relationships inferred by LLM between entities
- User Scoping: Episodes stored with `group_id` parameter for user isolation
- Semantic Search: Uses embeddings and hybrid search (semantic + keyword + graph traversal)

#### 3. **Tools** (`src/tools.py`)
- `WebSearchTool`: Tavily-powered web search
  - Searches web with configurable result count
  - Formats results with answer summaries and sources
- `ToolRegistry`: Registry pattern for extensible tools
  - Currently: `web_search`
  - Add new tools by adding methods and registering in `self.tools` dict

#### 4. **Configuration** (`src/config.py`)
- `OpenAIConfig`: OpenAI credentials and models (supports both Azure OpenAI and openai.com)
  - Main API key and endpoint (for chat/LLM)
  - Optional separate embedding API key and endpoint (for different Azure resource)
  - Chat model and embedding model names (deployment names for Azure)
  - Validates required fields (api_key)
- `Neo4jConfig`: Database connection parameters
- `TavilyConfig`: Web search API key
- `AgentConfig`: Agent behavior settings
- `validate_all_configs()`: Central validation function

### Data Flow
```
User Input
    ↓
SyncMemoryAgent.process_message() [sync wrapper]
    ↓
MemoryAgent.process_message() [async core]
    ├─ GraphitiMemory.get_context_for_query() → retrieve relevant memories
    ├─ _get_ai_response() with tools=[web_search]
    │  ├─ OpenAI AsyncOpenAI client chat completion
    │  └─ LLM decides if tool needed → tool_calls
    ├─ _handle_tool_calls()
    │  └─ _execute_tool_call("web_search") → Tavily search
    ├─ _get_ai_response() again with tool results
    │  └─ LLM generates final response using tool context
    └─ GraphitiMemory.add_episode(group_id=user_id) → store with user isolation
    ↓
Response to User
```

### Async/Sync Architecture
- **Async**: All core operations are async (LLM calls, knowledge graph operations)
- **Sync Wrapper**: CLI uses `SyncMemoryAgent` which manages event loop creation/cleanup
- **Event Loop Management**: Each sync instance creates dedicated event loop to avoid conflicts
- **Thread Safety**: Not thread-safe; designed for single-threaded CLI use

## Key Design Decisions

1. **Standard OpenAI Client**: Uses the official `openai` library (v1.50+) with `base_url` parameter for Azure OpenAI support, enabling compatibility with both Azure and openai.com
2. **Separate Resource Endpoints**: Supports separate Azure resources for chat and embeddings, enabling cost optimization and independent scaling
3. **Temporal Knowledge Graph**: Graphiti automatically extracts entities and relationships with timestamps, enabling temporal reasoning across conversation history
4. **LLM-Controlled Function Calling**: Uses OpenAI's `tools` parameter for intelligent tool usage decisions by LLM
5. **Group-Based User Isolation**: Uses Graphiti's `group_id` parameter instead of `user_id` to maintain separate knowledge graphs per user
6. **Conversation History Limits**: Configurable window (default 10 turns) to manage LLM context size while preserving long-term memory in knowledge graph
7. **Sync Wrapper Pattern**: Allows async internals while providing familiar sync API for CLI usage
8. **Episode-Based Storage**: Each conversation turn stored as discrete episode with full context for better temporal grounding and retrieval
9. **Hybrid Memory Search**: Graphiti's hybrid search combines semantic embeddings, keyword matching (BM25), and graph traversal
10. **Single Event Loop Architecture**: Single shared event loop between all components for clean resource management

## Common Development Tasks

### Adding a New Tool
1. Create tool class in `src/tools.py` (inherit from or implement similar interface)
2. Add to `ToolRegistry.__init__()`:
   ```python
   self.new_tool = NewTool()
   self.tools["new_tool_name"] = self.new_tool.method_name
   ```
3. Update agent's system prompt in `MemoryAgent._create_system_prompt()`

### Modifying Agent Behavior
- **System Prompt**: Update `MemoryAgent._create_system_prompt()`
- **Web Search Logic**: Modify `_should_use_web_search()` keywords
- **History Window**: Adjust `CONVERSATION_HISTORY_LIMIT` in `.env` or `AgentConfig`
- **Memory Relevance**: Adjust `num_results` in `process_message()`

### Debugging Knowledge Graph
```bash
# Access Neo4j Browser
open http://localhost:7474

# Query recent episodes (in Neo4j browser)
MATCH (ep:Episode) RETURN ep ORDER BY ep.reference_time DESC LIMIT 10
```

### Extending Configuration
1. Add new config class in `src/config.py`
2. Add validation method
3. Add to `validate_all_configs()`
4. Update `.env` template

## Development Progress & Roadmap

### Current Phase: Production Ready
**Timeline**: Completed - OpenAI Client Conversion and Full Graphiti Integration

#### Phase 1: Critical Setup & Dependencies ✅ COMPLETE
- [x] Install missing dependencies: `graphiti-core>=0.1.0`, `tavily-python>=0.3.0`
- [x] Start Neo4j database with `docker-compose up -d`
- [x] Verify end-to-end connectivity

#### Phase 2: Critical Bug Fixes ✅ COMPLETE
- [x] Fix user isolation: Use `group_id` parameter (not `user_id`) in `add_episode()` calls
- [x] Refactor event loop architecture: Single shared loop between components
- [x] Add `clear_history()` method to `SyncMemoryAgent` for proper encapsulation

#### Phase 3: OpenAI Client Conversion ✅ COMPLETE
- [x] Convert from `AsyncAzureOpenAI` to `AsyncOpenAI`
- [x] Implement `base_url` configuration for Azure OpenAI support
- [x] Support separate endpoints for chat and embeddings
- [x] Update OpenAIEmbedderConfig to use `embedding_model` parameter
- [x] Fix Graphiti search results handling (list instead of dict)
- [x] Update model parameters: `max_completion_tokens` and remove custom `temperature`
- [x] Full integration testing - episode creation, search, and memory retrieval verified

#### Phase 4: Function Calling Implementation ✅ COMPLETE
- [x] Define tool schemas for web_search using OpenAI's `tools` parameter format
- [x] Implement tool execution loop in `_get_ai_response()` and `process_message()`
- [x] Support multi-turn tool usage (tool → result → final response)

#### Phase 5: Error Handling & Robustness ✅ COMPLETE
- [x] Add graceful error recovery for memory search, web search, and episode storage
- [x] Python `logging` module integrated
- [x] Input validation for user messages and tool responses
- [x] Retry logic for transient failures

#### Phase 6: Testing & Validation ✅ COMPLETE
- [x] Episode creation and storage tested
- [x] Integration tests for memory storage and retrieval passing
- [x] Conversation flow with memory context verified
- [x] All agent components functional and integrated

### Known Issues & Fixes

**Issue 1: User Scoping Bug** ✅ FIXED
- **Location**: `src/agent.py:155-160`
- **Problem**: `add_episode()` doesn't pass `user_id`, causing memory contamination between users
- **Fix**: Use Graphiti's `group_id` parameter instead
- **Status**: ✅ COMPLETE - All `add_episode()` calls now use `group_id` for user isolation

**Issue 2: Event Loop Management** ✅ FIXED
- **Location**: `src/graphiti_client.py` & `src/agent.py`
- **Problem**: Multiple event loops created, potential conflicts
- **Fix**: Refactor to use single shared loop or `asyncio.run()` pattern
- **Status**: ✅ COMPLETE - Single event loop architecture implemented

**Issue 3: Azure OpenAI Client Library Conversion** ✅ FIXED
- **Location**: `src/agent.py`, `src/graphiti_client.py`, `src/config.py`
- **Problem**: AsyncAzureOpenAI has more restrictive API requirements and is Azure-specific
- **Fix**: Convert to standard `AsyncOpenAI` client with `base_url` parameter for Azure support
- **Status**: ✅ COMPLETE - All clients converted and tested
  - ✅ Updated imports to use `AsyncOpenAI` from `openai` library
  - ✅ Configured `base_url` for both chat and embedding endpoints
  - ✅ Support for separate Azure resources with optional separate API keys
  - ✅ All integration tests passing

**Issue 4: Graphiti Embedding Model Configuration** ✅ FIXED
- **Location**: `src/graphiti_client.py:74`
- **Problem**: OpenAIEmbedderConfig requires `embedding_model` parameter, not `model`
- **Fix**: Use correct parameter name `embedding_model` when initializing OpenAIEmbedderConfig
- **Status**: ✅ COMPLETE - Embeddings working correctly

**Issue 5: Model Parameter Incompatibilities** ✅ FIXED
- **Location**: `src/agent.py:141` (max_tokens) and `src/agent.py:140` (temperature)
- **Problem**: gpt-5-mini-nlq model doesn't support custom temperature or `max_tokens` parameter
- **Fix**: Removed temperature parameter, updated to use `max_completion_tokens`
- **Status**: ✅ COMPLETE - All chat completion requests working

**Issue 6: Search Results Format** ✅ FIXED
- **Location**: `src/graphiti_client.py:174-186`
- **Problem**: Graphiti search returns list of result objects, not dict with 'results' key
- **Fix**: Updated search result handling to treat results as a list
- **Status**: ✅ COMPLETE - Memory retrieval working correctly

## Dependencies and Versions

### Core Dependencies
- `graphiti-core>=0.1.0` - Temporal knowledge graph framework with LLM integration
- `openai>=1.50.0` - Standard OpenAI client library (supports both openai.com and Azure OpenAI via `base_url`)
- `python-dotenv>=1.0.0` - Environment variable management
- `tavily-python>=0.3.0` - Web search API client (v0.7.12+)
- `pydantic>=2.0.0` - Data validation and configuration management
- `neo4j>=5.0.0` - Neo4j database driver
- `python-asyncio` - Async/await support (built-in)

### Optional Dependencies
- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support
- `pytest-mock>=3.10.0` - Mocking support

### Verified Version Compatibility
- Python: 3.13+
- OpenAI client: 1.50.0+ (AsyncOpenAI with base_url support)
- Graphiti: 0.1.0+ (with proper embedding_model configuration)
- Neo4j: 5.26+

## Troubleshooting

### Neo4j Connection Failed
```bash
# Verify Docker is running
docker-compose ps

# Check Neo4j logs
docker-compose logs neo4j

# Restart Neo4j
docker-compose restart neo4j
```

### OpenAI Configuration Error
- Verify `OPENAI_API_KEY` is set and valid in `.env`
- Check `OPENAI_API_ENDPOINT` points to correct Azure resource endpoint
- Ensure `OPENAI_CHAT_MODEL` and `OPENAI_EMBEDDING_MODEL` match your Azure deployment names
- If using separate resources, verify `OPENAI_EMBEDDING_ENDPOINT` and optional `OPENAI_EMBEDDING_API_KEY`
- Common issue: Using model ID (e.g., "text-embedding-3-small") instead of deployment name (e.g., "embedding-3-small")

### Memory Not Persisting
- Check Neo4j is running: `docker-compose logs neo4j`
- Verify episodes are being stored: Check Neo4j browser at http://localhost:7474
- Check Graphiti initialization completes without errors

### Web Search Not Working
- Verify TAVILY_API_KEY is set and valid
- Check Tavily API quota hasn't been exceeded
- Review search heuristics if searches aren't triggering
