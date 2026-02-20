# How Memory Works — Graphiti and the Temporal Knowledge Graph

This document explains the theory behind the memory system and how it is implemented in this agent.

---

## The Problem with Traditional LLM Memory

Standard LLMs have no memory between sessions. A common workaround is to stuff recent conversation history into the context window — but this only works for short sessions and doesn't scale. After the window fills, old context is dropped and lost.

A better approach: store what the agent learns as **structured, searchable knowledge** in a database, and retrieve only the relevant parts when needed. This is what Graphiti provides.

---

## What Is Graphiti?

[Graphiti](https://github.com/getzep/graphiti) is an open-source Python framework for building **temporal knowledge graphs from conversational data**. It:

1. Receives a piece of text (an "episode" — e.g. a conversation turn)
2. Uses an LLM to extract **entities** (people, concepts, places, organizations) and the **relationships** between them
3. Stores everything in **Neo4j** as a graph with timestamps
4. Provides **hybrid search** — semantic (embedding-based) + keyword (BM25) + graph traversal — to retrieve relevant facts for a given query

The "temporal" part is key: every fact is stored with `valid_at` and `invalid_at` timestamps. If the agent learns "Alice works at Acme" and later learns "Alice now works at BetaCorp", Graphiti doesn't overwrite the old fact — it records that the first fact became invalid and a new one became valid. This lets the agent reason about how knowledge has changed over time.

---

## The Knowledge Graph Structure

The graph lives in Neo4j and has three types of nodes:

```
Episodic node  ──[MENTIONS]──▶  Entity node
                                    │
                               [RELATES_TO]
                                    │
                                    ▼
                               Entity node
```

### Node Types

**Episodic** — a raw conversation turn. Contains the full text of what was said, timestamps, and the `group_id` (user identifier).

```
(Episodic {
  uuid:        "abc-123",
  name:        "conversation_2026-01-15T10:23:44",
  content:     "User: I'm working on a RAG pipeline in Python.\nAgent: ...",
  group_id:    "adithya",
  valid_at:    2026-01-15T10:23:44,
  created_at:  2026-01-15T10:23:44
})
```

**Entity** — a named thing extracted from episodes: a person, technology, organization, concept, etc. Entities persist across episodes — if "Python" appears in ten conversations, there is one Python entity with ten MENTIONS edges pointing to it.

```
(Entity {
  uuid:        "xyz-789",
  name:        "Python",
  type:        "programming_language",
  group_id:    "adithya",
  created_at:  2026-01-15T10:23:44
})
```

**Community** — clusters of related entities automatically identified by Graphiti (similar to topic modeling). Less commonly queried directly.

### Edge Types

**MENTIONS** — links an Episodic node to each Entity it contains.

**RELATES_TO** — links two Entity nodes with a relationship (e.g. "Python `is_a` programming_language", "Alice `works_at` Acme"). These edges carry temporal properties:
- `valid_at` — when this relationship became true
- `invalid_at` — when it stopped being true (null if still current)
- `fact_embedding` — vector embedding for semantic search

---

## How an Episode Is Created

After every conversation turn, the agent creates an episode and hands it to Graphiti:

```python
# In agent.py (fire-and-forget background task)
await memory_client.add_episode(
    name=f"conversation_{datetime.now().isoformat()}",
    episode_body=f"User: {user_message}\nAgent: {final_response}",
    source=EpisodeType.text,
    source_description="Conversation turn",
    reference_time=datetime.now(),
    group_id=self.user_id,       # user isolation
)
```

Graphiti then:
1. Parses the episode body
2. Calls the LLM with a structured extraction prompt → gets back entity names, types, and relationships
3. Upserts Entity nodes (creates new ones or updates existing ones)
4. Creates RELATES_TO edges with temporal data
5. Stores the Episodic node linked to those entities via MENTIONS edges

This happens **in the background** (fire-and-forget). The user gets their response immediately; knowledge graph writes happen asynchronously with retry logic.

---

## How Memory Is Retrieved

At the start of every turn, before calling the LLM, the agent queries the knowledge graph:

```python
context = await memory_client.get_context_for_query(
    query=user_message,
    user_id=self.user_id,
    num_results=3,             # top 3 most relevant results
)
```

Graphiti runs a **hybrid search**:
- **Semantic search** — embeds the query and finds entities/relationships with similar fact embeddings
- **Keyword search (BM25)** — lexical matching over episode content
- **Graph traversal** — follows edges to surface related facts

Results are filtered by `group_id` so users only see their own data. The top results (capped at 1200 characters) are injected into the LLM prompt as context.

---

## The Full Memory Flow

```
Startup
└── Graphiti.initialize()
    └── build_indices_and_constraints()  ← Neo4j schema ready before first message

Turn N: User sends a message
├── 1. Memory retrieval
│   └── semantic search → top 3 relevant facts from past conversations
│       (15s timeout; returns empty if Neo4j is slow)
│
├── 2. LLM routing call
│   └── system prompt + memory context + user message + web_search tool
│       → LLM decides: answer directly or search the web
│
├── 3. (if tool called) Web search
│   └── Tavily API → results injected into next LLM call
│       (runs in thread pool, 30s timeout)
│
├── 4. LLM synthesis call
│   └── tool_choice="none" → forces text response
│       → final_response returned to user
│
└── 5. Background: Episode storage
    └── asyncio.ensure_future(_store_episode_background())
        ├── add_episode() → Graphiti entity extraction → Neo4j write
        └── retry on rate limit: 2s, 4s backoff (3 attempts)
```

---

## User Isolation

Every Episodic and Entity node is tagged with a `group_id` matching the user's identifier. All searches filter by this field:

```python
# In graphiti_client.py
results = await self._graphiti.search(
    query=query,
    group_ids=[user_id],   # only this user's data
)
```

To delete all data for a user:

```python
from graphiti_core.utils.maintenance.graph_data_operations import clear_data
await clear_data(graphiti.driver, group_ids=["alice"])
```

This is what the `delete user <id>` CLI command calls internally. It wipes all Episodic, Entity, and Community nodes where `group_id = alice`.

---

## Why Temporal Matters

Unlike a simple vector store (which just stores text chunks with embeddings), the temporal knowledge graph:

- **Deduplicates entities** — "Python" discussed in 50 conversations becomes one node with 50 incoming edges, not 50 duplicate entries
- **Tracks change over time** — "Alice works at Acme" (January) then "Alice works at BetaCorp" (March) are both stored, with the first marked invalid after March
- **Enables temporal queries** — "What do you know about Alice from last month?" can be answered by filtering on `valid_at` ranges
- **Builds a semantic web** — relationships between entities (Python → programming language → used in data science) are explicit edges, enabling graph traversal to surface non-obvious connections

---

## Inspecting Memory in Neo4j Browser

Open http://localhost:7474 (credentials: neo4j / password).

```cypher
-- Your recent episodes
MATCH (ep:Episodic {group_id: "adithya"})
RETURN ep.name, ep.content, ep.valid_at
ORDER BY ep.valid_at DESC LIMIT 10

-- Entities the agent knows about you
MATCH (ep:Episodic {group_id: "adithya"})-[:MENTIONS]-(e:Entity)
RETURN DISTINCT e.name, e.type

-- Relationships between entities
MATCH (a:Entity {group_id: "adithya"})-[r:RELATES_TO]-(b:Entity)
RETURN a.name, r.name, b.name, r.valid_at
ORDER BY r.valid_at DESC LIMIT 20

-- Total memory size per user
MATCH (ep:Episodic)
RETURN ep.group_id AS user, COUNT(ep) AS episodes
ORDER BY episodes DESC
```
