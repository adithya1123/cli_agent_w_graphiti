# Playbook: Run and Debug
_Last updated: 2026-04-25_

## Start the agent

```bash
# 1. Start Neo4j (required)
docker-compose up -d

# 2. Run the agent
python main.py
```

## Verify Neo4j is healthy

```bash
docker-compose ps
# Expected: neo4j container status "Up"

docker-compose logs neo4j | tail -20
# Look for: "Started."
```

## Reset Neo4j (wipes all data)

```bash
docker-compose down
rm -rf ./neo4j/data ./neo4j/logs
docker-compose up -d neo4j
```

## Key log lines to watch

| Log message | Meaning |
|-------------|---------|
| `INFO  Graphiti indices and constraints ready` | Schema ready — safe to use |
| `INFO  SyncMemoryAgent initialized for user: X` | Full startup complete |
| `INFO  Conversation episode stored in knowledge graph` | Memory write succeeded |
| `WARNING Episode storage failed (attempt N/3)` | Transient failure, will retry |
| `ERROR Episode storage permanently failed` | Neo4j or Graphiti is down |

## Run test scripts

```bash
python test_graphiti_simple.py     # Graphiti connectivity test
python test_episode_simple.py      # Episode storage test
python test_conversation.py        # Full conversation flow test
```

## Neo4j browser (inspect data)

Open http://localhost:7474 (user: `neo4j`, password: `password`)

Useful queries:
```cypher
-- Recent episodes for a user
MATCH (ep:Episodic {group_id: "alice"})
RETURN ep ORDER BY ep.valid_at DESC LIMIT 10

-- Entity graph for a user
MATCH (ep:Episodic {group_id: "alice"})-[:MENTIONS]-(e:Entity)
RETURN DISTINCT e.name, e.type

-- All users and episode counts
MATCH (ep:Episodic) WHERE ep.group_id IS NOT NULL
RETURN ep.group_id, COUNT(ep) ORDER BY COUNT(ep) DESC
```

## Common startup failures

**`Configuration Error: OPENAI_API_KEY not set`**: Create `.env` from `.env.example` and fill in required vars.

**`Error initializing agent: ... Make sure Neo4j is running`**: Docker is not running or Neo4j container failed. Run `docker-compose up -d` and check `docker-compose logs neo4j`.

**Blank responses from the agent**: `max_completion_tokens` too low for the model. Increase synthesis call limit in `_handle_tool_calls()` in `src/agent.py`.

**Entity extraction not happening**: Check `GRAPHITI_LLM_MODEL` — if your chat model is a reasoning/o-series model, set this to `gpt-4o-mini` or similar.

→ See also: `01_hazards.md`, `contracts/graphiti_client.md`, `contracts/config.md`
