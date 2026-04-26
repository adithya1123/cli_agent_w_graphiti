# Module Narratives
_Last updated: 2026-04-25_

Plain-English explanations of each subsystem. Use this when asked to explain
what part of the codebase does, or to give a new developer orientation.

---

## agent (`src/agent.py`)

**One-line purpose**: The brain — orchestrates LLM calls, memory retrieval, tool use, and episode storage for each conversation turn.

**Why it exists**: Central coordinator that glues together the OpenAI client, Graphiti memory, and tools into a single `process_message()` call. The async/sync split (`MemoryAgent` / `SyncMemoryAgent`) exists because the underlying libraries are async but the CLI loop is synchronous.

**What it does in plain English**:
When the user sends a message, the agent first fetches relevant memories from the knowledge graph (with a 15-second timeout). It then sends the message plus memory context to the LLM. If the LLM decides to use a tool (e.g. web search), the agent runs the tool, feeds the result back to the LLM in a second call, and returns the synthesized response. After returning the response, it asynchronously stores the conversation as an episode in Neo4j.

**Key concepts**:
- Two-call LLM pattern: routing call (decides whether to use tools) + synthesis call (forced text response via `tool_choice="none"`)
- Episode storage is fire-and-forget — the user never waits for it
- Error responses are filtered from history to avoid poisoning the context window
- `SyncMemoryAgent` owns and manages the event loop; `MemoryAgent` is always used inside it

**What it does NOT do**:
- Does not validate user IDs — that's `user_session.py`
- Does not connect to Neo4j directly — that's `graphiti_client.py`
- Does not implement the CLI REPL — that's `main.py`

**Failure signature**:
- `"Connection error: Could not reach Azure OpenAI service"` → network or endpoint config issue
- `"Authentication error: Please check your API credentials"` → bad `OPENAI_API_KEY`
- `"Deployment not found:"` → wrong `OPENAI_CHAT_MODEL` for Azure
- Blank/empty responses → `max_completion_tokens` too low on synthesis call (reasoning models)
- `"Graphiti not initialized"` → `initialize()` was not called before use

→ See also: `contracts/agent.md`, `01_hazards.md`

---

## graphiti_client (`src/graphiti_client.py`)

**One-line purpose**: The memory layer — wraps Graphiti to store, search, and delete conversation knowledge scoped per user.

**Why it exists**: Isolates all Graphiti and Neo4j interaction behind a clean async interface. The agent only calls `get_context_for_query()`, `add_episode()`, `list_users()`, and `delete_user()` — it never touches Graphiti or Neo4j APIs directly.

**What it does in plain English**:
On initialization, it creates two OpenAI async clients (one for Graphiti's LLM calls, one for embeddings — these can be different Azure resources), constructs a `Graphiti` instance connected to Neo4j, and blocks until Neo4j's schema (indices and constraints) is ready. After that, every conversation turn is stored as an `Episodic` node and Graphiti runs entity extraction in the background to build out the knowledge graph. Memory search uses Graphiti's vector search scoped to the current user's `group_id`.

**Key concepts**:
- `GraphitiMemoryClient` is the active class; `GraphitiMemory` is a legacy sync wrapper not used in the main flow
- `build_indices_and_constraints()` is called eagerly and "already exists" errors are suppressed — safe to call on every startup
- Embedding and LLM can come from separate Azure resources (`OPENAI_EMBEDDING_ENDPOINT` / `OPENAI_EMBEDDING_API_KEY`)

**What it does NOT do**:
- Does not own the event loop — that's `SyncMemoryAgent`
- Does not manage user sessions or validate user IDs
- Does not render visualizations — that's `visualizer.py` (which opens its own Neo4j driver)

**Failure signature**:
- `"Graphiti not initialized. Call initialize() first."` → method called before `initialize()` ran
- Neo4j connection errors at startup → Docker not running, wrong `NEO4J_URI`
- `"Index initialization warning: ..."` (not "already exists") → schema setup issue, check Neo4j logs

→ See also: `contracts/graphiti_client.md`, `01_hazards.md`, `02_business_logic.md`

---

## tools (`src/tools.py`)

**One-line purpose**: Tool registry — wraps Tavily web search and exposes it to the agent via a uniform `call_tool()` interface.

**Why it exists**: Decouples tool implementation from the agent. The agent only calls `ToolRegistry.call_tool("web_search", query=...)` — adding a new tool requires changes here and in the agent's tool definitions, not in the agent's core logic.

**What it does in plain English**:
`WebSearchTool` wraps the Tavily client. When called, it searches the web, gets back a JSON response with an AI-generated answer and source URLs, and formats it into a readable string for the LLM. `ToolRegistry` is a thin registry that maps tool names to their callable handlers.

**What it does NOT do**:
- Does not run asynchronously — tool calls are wrapped in `asyncio.to_thread()` in the agent
- Does not cache search results
- Does not implement any tools other than web search

**Failure signature**:
- `"Search service not available"` → Tavily client failed to initialize (bad `TAVILY_API_KEY`)
- `"Search failed: ..."` → Tavily API error, surfaced to the LLM as a tool result string

→ See also: `contracts/tools.md`, `playbooks/add_tool.md`

---

## config (`src/config.py`)

**One-line purpose**: Environment variable configuration — reads `.env`, provides typed config classes, validates required vars at startup.

**Why it exists**: Single source of truth for all env var names. Any time an env var is added or renamed, only this file changes.

**What it does in plain English**:
On import, loads `.env` from the project root. Each config class (`OpenAIConfig`, `Neo4jConfig`, `TavilyConfig`, `AgentConfig`) is a plain class with class-level attributes set from `os.getenv()`. `validate_all_configs()` is called at startup in `main()` and raises `ValueError` with a clear message if a required var is missing.

**What it does NOT do**:
- Does not use Pydantic models (despite Pydantic being in the stack — these are plain classes)
- Does not validate values beyond presence (`api_key not None`)

**Failure signature**:
- `"OPENAI_API_KEY not set in environment"` → missing `.env` or unset var
- Config silently uses defaults for optional vars (e.g. `NEO4J_URI` defaults to `bolt://localhost:7687`)

→ See also: `contracts/config.md`, `playbooks/add_config_var.md`

---

## user_session (`src/user_session.py`)

**One-line purpose**: Persists the last-used user ID across CLI sessions in `~/.agent_memory/last_user`.

**Why it exists**: Users shouldn't have to type their name every time they start the CLI. The session file lets the CLI pre-fill the prompt with the last user.

**What it does in plain English**:
On startup, `prompt_for_user()` reads the last user from `~/.agent_memory/last_user` and shows it as a default. If the user presses Enter, the default is used. New user IDs are validated (alphanumeric, hyphens, underscores, 1-50 chars) before being saved.

**What it does NOT do**:
- Does not authenticate users — any valid string becomes a user ID
- Does not list users — that comes from Neo4j via `GraphitiMemoryClient.list_users()`

→ See also: `contracts/user_session.md`

---

## visualizer (`src/visualizer.py`)

**One-line purpose**: Generates an interactive HTML knowledge graph visualization for a user's Neo4j data, opens it in the browser.

**Why it exists**: Provides a debugging and exploration view of what the agent has learned about a user. Helps developers verify that Graphiti is extracting entities and building relationships correctly.

**What it does in plain English**:
Opens a direct Neo4j driver connection (independent of Graphiti), fetches `Episodic` and `Entity` nodes for the target user (optionally filtered by time range), and renders them as an interactive vis.js graph in a temporary HTML file. The file is opened automatically in the default browser.

**What it does NOT do**:
- Does not show `:RELATES_TO` (entity-to-entity) edges — only `:MENTIONS` (episode-to-entity)
- Does not use Graphiti's client — queries Neo4j directly with Cypher

**Failure signature**:
- Neo4j connection error at `GraphVisualizer()` construction → Docker not running
- `"No conversation data found for user '{user_id}'"` → user has no episodes yet (printed, not raised)
- Blank graph with nodes but no edges → Graphiti's entity extraction hasn't run yet or found no entities

→ See also: `contracts/visualizer.md`

---

## main (`main.py`)

**One-line purpose**: The CLI REPL — reads user input, dispatches commands, and delegates to `SyncMemoryAgent`.

**Why it exists**: Thin entry point that separates CLI concerns (display, input, command parsing) from agent logic.

**What it does in plain English**:
On startup, validates config, prompts for user ID, and initializes `SyncMemoryAgent` (which eagerly initializes Graphiti). Then runs a `while True` input loop. Special commands (`help`, `whoami`, `switch`, `users`, `delete user`, `visualize`, `clear`) are handled inline. Everything else is forwarded to `agent.process_message()`.

**What it does NOT do**:
- Does not implement any agent logic — purely CLI dispatch
- Does not maintain any state beyond `user_id` and the `agent` instance

→ See also: `contracts/main.md`, `playbooks/add_cli_command.md`
