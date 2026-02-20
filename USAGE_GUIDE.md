# Usage Guide

Complete guide for setting up and using the Memory Agent from scratch.

---

## Prerequisites

- **Python 3.13+** — check with `python --version`
- **Docker Desktop** — for running Neo4j
- **uv** — Python package manager ([install](https://docs.astral.sh/uv/getting-started/installation/))
- **OpenAI API credentials** — Azure OpenAI or openai.com
- **Tavily API key** — for web search ([tavily.com](https://tavily.com))

---

## First-Time Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd cli_agent_w_graphiti
uv sync
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# ── LLM (Chat) ──────────────────────────────────────────────────────────────
OPENAI_API_KEY=your-api-key
OPENAI_CHAT_MODEL=gpt-4o

# For Azure OpenAI — set the v1 endpoint:
OPENAI_API_ENDPOINT=https://<resource>.cognitiveservices.azure.com/openai/v1/

# ── Embeddings ───────────────────────────────────────────────────────────────
# If using the same resource as chat, only set the model name:
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# If using a separate Azure resource for embeddings (optional):
OPENAI_EMBEDDING_ENDPOINT=https://<other-resource>.cognitiveservices.azure.com/openai/v1/
OPENAI_EMBEDDING_API_KEY=separate-key-if-needed

# ── Graphiti internal LLM (optional) ────────────────────────────────────────
# Set this if your chat model is an o-series/reasoning model (e.g. o3, gpt-5-mini-nlq).
# Graphiti needs structured outputs for entity extraction — reasoning models may not
# support this. Point GRAPHITI_LLM_MODEL to a standard model (e.g. gpt-4o-mini).
GRAPHITI_LLM_MODEL=

# ── Neo4j ────────────────────────────────────────────────────────────────────
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# ── Web Search ───────────────────────────────────────────────────────────────
TAVILY_API_KEY=your-tavily-key

# ── Agent ────────────────────────────────────────────────────────────────────
AGENT_NAME=Knowledge Graph Agent
CONVERSATION_HISTORY_LIMIT=10
```

**Azure vs openai.com:**
- **openai.com**: set `OPENAI_API_KEY` and `OPENAI_CHAT_MODEL`. Leave `OPENAI_API_ENDPOINT` empty.
- **Azure OpenAI**: set `OPENAI_API_ENDPOINT` to the v1 endpoint format shown above. `OPENAI_CHAT_MODEL` is your deployment name (not the base model name).

### 3. Start Neo4j

```bash
docker-compose up -d neo4j

# Verify it's healthy (wait ~15 seconds after starting)
docker-compose ps
```

You should see `(healthy)` in the STATUS column. Neo4j browser is available at http://localhost:7474 (user: `neo4j`, password: `password`).

### 4. Run the agent

```bash
python main.py
```

On first run, you'll be prompted for a username. This is used to namespace your memory — any alphanumeric string works (e.g. `alice`, `adithya`). The agent saves your last username and offers it as the default on subsequent runs.

---

## Daily Usage

```bash
# Start the agent
python main.py

# Neo4j must be running — if you restarted Docker:
docker-compose up -d neo4j
```

---

## CLI Commands

All commands are typed at the `You:` prompt.

### Chat
Just type your message. The agent retrieves relevant memories, decides whether to search the web, and responds.

```
You: What did I tell you about my project last week?
You: What's the latest news on LLM benchmarks?
You: Remember that I prefer concise answers
```

### User Management

```
users
```
Lists all users that have memory data in Neo4j, with episode counts. Current user is marked.

```
  User ID                          Episodes
  ------------------------------------------
  adithya                               142  ← current
  alice                                  38
```

```
delete user <user_id>
```
Permanently deletes all memory data (episodes, entities, relationships) for the specified user. Prompts for confirmation. If you delete yourself, you'll be prompted to choose a new user.

```
whoami
```
Shows your current username.

```
switch
```
Prompts for a new username and reinitializes the agent with that user's memory context.

### Memory & History

```
clear
```
Clears the in-session conversation history (the last N messages sent to the LLM). Does **not** delete anything from the knowledge graph — long-term memory is unaffected.

### Visualization

```
visualize          — all-time knowledge graph
visualize 7        — last 7 days
visualize 30       — last 30 days
```

Generates an interactive HTML file and opens it in your browser. Nodes represent entities and episodes; edges show relationships. Click and drag to explore, scroll to zoom.

### Other

```
help    — show command list
exit    — quit (also: quit, Ctrl+C)
```

---

## Programmatic Usage

```python
from src.agent import SyncMemoryAgent

# Basic usage
agent = SyncMemoryAgent(user_id="alice")
response = agent.process_message("What do you know about me?")
print(response)
agent.close()

# Context manager (auto-closes)
with SyncMemoryAgent(user_id="alice") as agent:
    r1 = agent.process_message("My name is Alice and I work in ML")
    r2 = agent.process_message("What did I just tell you?")
    print(r2)

# Clear in-session history
agent.clear_history()

# List users (returns list of dicts: [{user_id, episode_count}])
users = agent.list_users()

# Delete a user
result = agent.delete_user("alice")
# result: {"deleted": True, "episodes_removed": 42}
```

---

## Neo4j Management

### Fresh start (wipe all data)

```bash
docker-compose down
rm -rf ./neo4j/data ./neo4j/logs
docker-compose up -d neo4j
```

### Inspect data in Neo4j browser

Open http://localhost:7474 and run Cypher queries:

```cypher
-- See all episodes for a user
MATCH (ep:Episodic {group_id: "alice"})
RETURN ep ORDER BY ep.valid_at DESC LIMIT 20

-- See entities for a user
MATCH (ep:Episodic {group_id: "alice"})-[:MENTIONS]-(e:Entity)
RETURN DISTINCT e.name, e.type LIMIT 50

-- Count data per user
MATCH (ep:Episodic)
WHERE ep.group_id IS NOT NULL
RETURN ep.group_id, COUNT(ep) AS episodes
ORDER BY episodes DESC

-- Count edges (should be > 0 after a few conversations)
MATCH ()-[r:RELATES_TO]-() RETURN COUNT(r) AS edges
```

### Restart Neo4j (without wiping data)

```bash
docker-compose restart neo4j
```

---

## Troubleshooting

### Agent fails to start: "Graphiti not initialized" or Neo4j errors

```bash
# Check Neo4j is running
docker-compose ps

# Check Neo4j logs
docker-compose logs neo4j

# Restart it
docker-compose restart neo4j
```

### "OPENAI_API_KEY not set" or API errors

- Verify your `.env` file exists and has no typos
- For Azure: ensure `OPENAI_API_ENDPOINT` ends with `/openai/v1/`
- For Azure: `OPENAI_CHAT_MODEL` should be your **deployment name**, not the base model name (e.g. `my-gpt4o-deployment`, not `gpt-4o`)

### Agent responds but memory doesn't persist

- Check Neo4j is healthy: `docker-compose ps`
- After a few conversations, verify episodes exist in Neo4j browser:
  ```cypher
  MATCH (ep:Episodic) RETURN COUNT(ep)
  ```
- Enable debug logging to see storage status:
  ```python
  # In main.py, change:
  setup_logging(log_level="DEBUG")
  ```

### Reasoning model returns blank responses

If using an o-series model (e.g. `o3`, `gpt-5-mini-nlq`), set `GRAPHITI_LLM_MODEL` to a standard model like `gpt-4o-mini` for Graphiti's entity extraction. Reasoning models consume their token budget on internal reasoning and may not support structured outputs.

### Web search not triggering

Web search is LLM-controlled — the model decides when it's needed. For queries about current events or recent data, it should trigger automatically. Verify `TAVILY_API_KEY` is set correctly.

### Slow first response

Normal — startup initializes Neo4j indices and the Graphiti schema. Subsequent responses are faster (~2–4 seconds total).

---

## Logging

Log output goes to the console by default. Change the level in `main.py`:

```python
setup_logging(log_level="DEBUG")   # verbose
setup_logging(log_level="WARNING") # quiet
```

Key log lines to watch:
```
INFO  - Graphiti indices and constraints ready          ← schema is ready
INFO  - Agent initialized for user: alice              ← startup complete
INFO  - Conversation episode stored                    ← memory saved (background)
WARNING - Episode storage failed (attempt 1/3)         ← transient, will retry
```
