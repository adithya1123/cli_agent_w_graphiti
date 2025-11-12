# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **Azure OpenAI Agent with Graphiti Temporal Knowledge Graph Memory** - a conversational AI system that learns and remembers information from past conversations using a temporal knowledge graph stored in Neo4j.

### Key Features
- **Temporal Knowledge Graph**: Uses Graphiti library to store facts with timestamps in Neo4j
- **Azure OpenAI Integration**: Leverages Azure OpenAI for LLM responses and embeddings
- **LLM-Controlled Web Search**: Uses OpenAI function calling for intelligent web search decisions
- **Conversation Memory**: Maintains context across multiple turns and learns from past conversations
- **Sync/Async Architecture**: Async processing with sync CLI wrapper for easy use
- **User Isolation**: Maintains separate memory graphs per user using Graphiti's `group_id` parameter

### Development Status
**Stage**: Active Development (Phase 1-3 in progress)
- Foundation: ✅ Complete (config, basic structures)
- Dependencies: ⏳ Installing (graphiti-core, tavily-python)
- Neo4j Setup: ⏳ Starting database
- Function Calling: 🔨 In Development
- Error Handling: 📋 Planned
- Testing: 📋 Planned

## Technology Stack
- **Python 3.13+**
- **LLM/Embeddings**: Azure OpenAI (gpt-4o, text-embedding-3-small)
- **Knowledge Graph**: Neo4j 5.26 + Graphiti
- **Web Search**: Tavily API
- **Config**: python-dotenv, Pydantic v2
- **Framework**: Async/await with asyncio

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
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_API_ENDPOINT=<your-endpoint>
AZURE_OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=embedding-3-small
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
TAVILY_API_KEY=<your-key>
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
  - Initializes Graphiti with Azure OpenAI LLM and embedder
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
- `AzureOpenAIConfig`: Azure OpenAI credentials and models
  - Validates required fields (api_key, api_endpoint)
  - Defaults for API version and deployment names
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
    │  ├─ Azure OpenAI chat completion
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

1. **Temporal Knowledge Graph**: Graphiti automatically extracts entities and relationships with timestamps, enabling temporal reasoning across conversation history
2. **LLM-Controlled Function Calling**: Uses Azure OpenAI's `tools` parameter (not deprecated `functions`) for intelligent tool usage decisions by LLM
3. **Group-Based User Isolation**: Uses Graphiti's `group_id` parameter instead of `user_id` to maintain separate knowledge graphs per user
4. **Conversation History Limits**: Configurable window (default 10 turns) to manage LLM context size while preserving long-term memory in knowledge graph
5. **Sync Wrapper Pattern**: Allows async internals while providing familiar sync API for CLI usage
6. **Episode-Based Storage**: Each conversation turn stored as discrete episode with full context for better temporal grounding and retrieval
7. **Hybrid Memory Search**: Graphiti's hybrid search combines semantic embeddings, keyword matching (BM25), and graph traversal
8. **Single Event Loop Architecture**: Shared event loop between GraphitiMemory and SyncMemoryAgent for clean resource management

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

### Current Phase: Graphiti Azure OpenAI Integration
**Timeline**: Active Development - Awaiting Azure v1 API Opt-in

#### Phase 1: Critical Setup & Dependencies ✅ COMPLETE
- [x] Install missing dependencies: `graphiti-core>=0.1.0`, `tavily-python>=0.3.0`
- [x] Start Neo4j database with `docker-compose up -d`
- [x] Verify end-to-end connectivity

#### Phase 2: Critical Bug Fixes ✅ COMPLETE
- [x] Fix user isolation: Use `group_id` parameter (not `user_id`) in `add_episode()` calls
- [x] Refactor event loop architecture: Single shared loop between components
- [x] Add `clear_history()` method to `SyncMemoryAgent` for proper encapsulation

#### Phase 3: Graphiti Azure OpenAI Integration ⏳ IN PROGRESS
- [x] Identify Azure OpenAI v1 API requirement for Structured Outputs (Responses API)
- [x] Implement Graphiti LLMConfig with Azure deployment names
- [x] Add OpenAIRerankerClient (cross_encoder) for Azure OpenAI
- [x] Test initialization and episode creation
- ⏳ **BLOCKED**: Azure deployment requires v1 API opt-in (404 error on responses.parse())
- [ ] **NEXT**: Enable v1 API opt-in on Azure OpenAI deployment (user responsibility)
- [ ] Verify episode creation works with v1 API enabled
- [ ] Test hybrid memory search with stored episodes

#### Phase 4: Function Calling Implementation ⏳ PLANNED
- [ ] Define tool schemas for web_search using Azure's `tools` parameter format
- [ ] Implement tool execution loop in `_get_ai_response()` and `process_message()`
- [ ] Remove keyword-based heuristic (`_should_use_web_search()`)
- [ ] Support multi-turn tool usage (tool → result → final response)

#### Phase 5: Error Handling & Robustness ⏳ PLANNED
- [ ] Add graceful error recovery for memory search, web search, and episode storage
- [ ] Replace `print()` statements with Python `logging` module (partially done)
- [ ] Add input validation for user messages and tool responses
- [ ] Implement retry logic for transient failures

#### Phase 6: Testing & Validation ⏳ PLANNED
- [ ] Create unit tests for ToolRegistry and configuration
- [ ] Create integration tests for memory storage and retrieval
- [ ] Manual testing: Basic conversation, web search, multi-turn, error scenarios
- [ ] Performance validation: Memory search latency, Neo4j usage

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

**Issue 3: Graphiti Azure OpenAI v1 API Requirement** ⏳ BLOCKED
- **Location**: `src/graphiti_client.py:38-89`
- **Problem**: Graphiti uses `client.beta.chat.completions.parse()` (Responses API) which requires Azure OpenAI v1 API opt-in
- **Error**: 404 Resource not found on `responses.parse()` endpoint
- **Root Cause**: Azure deployment doesn't have v1 API opt-in enabled
- **Solution**: User must enable v1 API opt-in on Azure deployment (see instructions below)
- **Implemented Fix** (waiting for v1 opt-in):
  - ✅ Added `LLMConfig` with Azure deployment names to `OpenAIClient`
  - ✅ Added `OpenAIRerankerClient` (cross_encoder) for Azure OpenAI
  - Code is ready; just needs v1 API enabled on Azure side

**Issue 4: Function Calling Not Implemented** ⏳ PLANNED
- **Location**: `src/agent.py:_get_ai_response()`
- **Problem**: Web search triggered by heuristic, not by LLM decision
- **Fix**: Implement Azure OpenAI `tools` parameter with execution loop
- **Status**: Planned for Phase 4 - will use chat completions with tool support

### How to Enable Azure OpenAI v1 API Opt-In

**Required for Graphiti Responses API (Structured Outputs):**
The official Graphiti docs require: `client.beta.chat.completions.parse()`

**Steps to enable on your Azure deployment:**
1. Go to Azure Portal or Azure AI Foundry
2. Navigate to your Azure OpenAI resource
3. Find Settings → API Version Management (or Preview Features)
4. Enable **v1 API opt-in** for your deployment (gpt-5-mini)
5. Wait a few minutes for propagation
6. Restart the agent application

**Reference:** https://learn.microsoft.com/en-us/azure/ai-foundry/openai/api-version-lifecycle?tabs=key#api-evolution

## Dependencies and Versions

- `graphiti-core>=0.1.0` - Temporal knowledge graph framework (requires LLM supporting structured output)
- `openai>=1.50.0` - Azure OpenAI client library (supports `tools` parameter)
- `python-dotenv>=1.0.0` - Environment variable management
- `tavily-python>=0.3.0` - Web search API client (latest v0.7.12)
- `pydantic>=2.0.0` - Data validation

**Dev Dependencies** (to be added):
- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support
- `pytest-mock>=3.10.0` - Mocking support

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

### Azure OpenAI Configuration Error
- Verify all required env vars are set in `.env`
- Check API version is recent (2025-01-01-preview or later)
- Ensure chat_deployment_name and embedding_deployment_name match your Azure resource

### Memory Not Persisting
- Check Neo4j is running: `docker-compose logs neo4j`
- Verify episodes are being stored: Check Neo4j browser at http://localhost:7474
- Check Graphiti initialization completes without errors

### Web Search Not Working
- Verify TAVILY_API_KEY is set and valid
- Check Tavily API quota hasn't been exceeded
- Review search heuristics if searches aren't triggering
