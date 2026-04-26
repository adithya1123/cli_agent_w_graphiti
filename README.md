# Memory Agent — OpenAI + Graphiti Temporal Knowledge Graph

A conversational AI agent that **remembers what you tell it across sessions**. Every conversation is stored in a temporal knowledge graph (Neo4j + Graphiti), so the agent can recall facts, understand context from past sessions, and reason about what it knows and when it learned it.

Built on the standard OpenAI client library — works with Azure OpenAI and openai.com.

---

## What It Does

- **Persistent memory across sessions** — facts from past conversations are retrieved and used as context in future ones. Close the app, come back a week later, and the agent still knows what you discussed.
- **Temporal knowledge graph** — memory is stored as a graph of entities and relationships with timestamps. The agent knows not just *what* it learned, but *when*.
- **Intelligent web search** — uses OpenAI function calling to decide when to search the web (via Tavily). No hardcoded heuristics — the LLM decides.
- **Multi-user support** — each user has a completely isolated memory graph. Switch between users at runtime.
- **User management** — list all users, delete a user's memory data from the CLI.
- **Interactive graph visualization** — generate an HTML visualization of any user's knowledge graph, filterable by time range.

---

## Features

| Feature | Details |
|---------|---------|
| Memory backend | Neo4j 5.26 + Graphiti temporal knowledge graph |
| LLM | OpenAI client v1.50+ (Azure OpenAI or openai.com) |
| Web search | Tavily API, triggered by LLM function calling |
| Embeddings | Configurable — can use a separate Azure resource |
| User isolation | Per-user memory via Graphiti `group_id` |
| Async architecture | Async core, sync CLI wrapper |
| Conversation history | Configurable sliding window (default: 10 turns) |
| Visualization | Interactive HTML graph via vis.js, auto-opens in browser |

---

## Architecture Overview

```
User Input
    ↓
Memory Retrieval  — semantic search of past conversations (Neo4j/Graphiti)
    ↓
LLM Routing Call  — with web_search tool available; LLM decides if search needed
    ↓ (if tool called)
Web Search        — Tavily API, runs in thread pool, 30s timeout
    ↓
LLM Synthesis     — generates final response with memory + search context
    ↓
Response to User
    ↓ (background)
Episode Storage   — conversation turn stored in knowledge graph (fire-and-forget)
```

### Core Components

| File | Role |
|------|------|
| `main.py` | CLI entry point, command dispatch |
| `src/agent.py` | `MemoryAgent` (async core) + `SyncMemoryAgent` (CLI wrapper) |
| `src/graphiti_client.py` | Graphiti/Neo4j wrapper — episode storage, search, user management |
| `src/tools.py` | Tavily web search tool |
| `src/config.py` | Environment variable configuration |
| `src/user_session.py` | User session persistence (`~/.agent_memory/`) |
| `src/visualizer.py` | Interactive Neo4j graph visualization |

---

## CLI Commands

```
users               — list all users with memory data and episode counts
delete user <id>    — permanently delete a user's memory (with confirmation)
whoami              — show current user
switch              — switch to a different user
visualize [N]       — visualize knowledge graph (N = 7, 30, or blank for all time)
clear               — clear in-session conversation history
help                — show command list
exit / quit         — exit
```

---

## Quick Start

See [USAGE_GUIDE.md](USAGE_GUIDE.md) for full setup instructions.

```bash
# 1. Clone and install
git clone <repo> && cd cli_agent_w_graphiti
uv sync

# 2. Configure
cp .env.example .env   # fill in API keys

# 3. Start Neo4j
docker-compose up -d neo4j

# 4. Run
python main.py
```

---

## Documentation

| Document | What it covers |
|----------|---------------|
| [USAGE_GUIDE.md](USAGE_GUIDE.md) | First-time setup, environment config, all usage patterns |
| [GRAPHITI_MEMORY.md](GRAPHITI_MEMORY.md) | How Graphiti and episodic memory work in this agent |
| [CLAUDE.md](CLAUDE.md) | Architecture details and development reference |
| [AGENTS/](AGENTS/) | Structured agent memory — module contracts, hazards, playbooks, narratives |

---

## Tech Stack

- Python 3.13+
- [Graphiti](https://github.com/getzep/graphiti) — temporal knowledge graph framework
- Neo4j 5.26 — graph database
- OpenAI client v1.50+ — LLM and embeddings
- Tavily — web search API
- Docker — Neo4j container
