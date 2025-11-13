# How Episodes Are Built - Quick Summary

## One-Sentence Overview
**Episodes are conversation turns (user question + agent answer) that get packaged with metadata and sent to Graphiti for automatic entity extraction and storage in Neo4j.**

## The Build Process (Step by Step)

### Step 1: Conversation Completes
```python
# In src/agent.py, after LLM responds
user_message = "What is Python?"
final_response = "Python is a high-level programming language..."
```

### Step 2: Create Episode Body
```python
episode_body = f"User: {user_message}\nAgent: {final_response}"
# Result:
# "User: What is Python?
#  Agent: Python is a high-level programming language..."
```

### Step 3: Build Episode with Metadata
```python
await self.memory_client.add_episode(
    name=f"conversation_{datetime.now().isoformat()}",
    # ↑ Unique ID like: "conversation_2025-11-11T19:55:49.123456"

    episode_body=episode_body,
    # ↑ The actual Q&A content

    source="agent_conversation",
    # ↑ Where this came from (string)

    source_description=f"Conversation turn between user and {self.agent_config.name}",
    # ↑ Human-readable context

    reference_time=datetime.now(),
    # ↑ When did this happen

    group_id=self.user_id,
    # ↑ Which user (for isolation)
)
```

### Step 4: Graphiti Processes Episode
Inside `GraphitiMemoryClient.add_episode()`:

```python
# Validate
if not self._graphiti:
    raise RuntimeError("Graphiti not initialized")

# Set defaults
if reference_time is None:
    reference_time = datetime.now()

if source_description is None:
    source_description = f"Episode from {source}"

# Convert source to enum (required by Graphiti)
source_enum = EpisodeType.text  # or json, or md
if source.lower() == "json":
    source_enum = EpisodeType.json

# Build kwargs
kwargs = {
    "name": name,
    "episode_body": episode_body,
    "source": source_enum,  # ← As enum, not string!
    "source_description": source_description,
    "reference_time": reference_time,
}
if group_id:
    kwargs["group_id"] = group_id

# Send to Graphiti
await self._graphiti.add_episode(**kwargs)
```

### Step 5: Graphiti's Processing
```
Episode received by Graphiti
    ↓
1. Parse episode_body: "User: What is Python?..."
    ↓
2. Call Azure OpenAI LLM:
   "Extract entities and relationships from this text"
    ↓
3. LLM returns:
   Entities: [Python, programming_language]
   Relationships: [Python is_a programming_language]
    ↓
4. Store in Neo4j:
   - Create Episode node
   - Create Entity nodes
   - Create relationship edges
   - Add temporal data
    ↓
5. Link to user: group_id = "demo_user"
```

### Step 6: Neo4j Storage
```
(Episode {
  uuid: "unique-id",
  name: "conversation_2025-11-11T19:55:49...",
  group_id: "demo_user",
  created_at: 2025-11-11 19:55:49,
  valid_at: 2025-11-11 19:55:49,
  content: "User: What is Python?...",
  source: "agent_conversation"
})

-[RELATES_TO {name: "mentioned_in"}]->

(Entity {
  name: "Python",
  type: "programming_language",
  created_at: 2025-11-11 19:55:49
})
```

### Step 7: Ready for Search
```python
# Now when user asks a new question:
await self.memory_client.get_context_for_query(
    query="Tell me about programming",
    group_id="demo_user"
)

# Graphiti searches Neo4j:
# "Find all entities related to 'programming' for user 'demo_user'"
# Returns: Python (from previous episode)
# Used as context: "You previously mentioned: Python is..."
```

## The 6 Key Components

| Component | What It Is | Example | Why It Matters |
|-----------|-----------|---------|----------------|
| **name** | Unique episode ID | `conversation_2025-11-11T19:55:49` | Identifies each conversation turn |
| **episode_body** | Full conversation | `User: What is Python?\nAgent: Python is...` | Contains content to extract entities from |
| **source** | Format type (enum) | `EpisodeType.text` | Tells Graphiti how to parse the content |
| **source_description** | Context about source | `Conversation turn between user and Agent` | Explains where this data came from |
| **reference_time** | Timestamp | `2025-11-11 19:55:49` | When did the conversation happen |
| **group_id** | User identifier | `demo_user` | Keeps user data isolated |

## Current Issue & Status

### What Works ✅
- Episode structure is correct
- All parameters properly set
- Event loop handling fixed
- Async/await architecture correct

### What Fails ⚠️
- Graphiti's LLM client can't use Azure OpenAI Responses API
- Error: "Azure OpenAI Responses API is enabled only for api-version 2025-03-01-preview and later"
- API version is set in `.env` but not reaching the actual API call

### Why It Matters
Without working entity extraction, episodes are stored as raw text but not processed into searchable entities. The agent still works (memory gracefully skips), but temporal knowledge graph is not populated.

## Three Solution Approaches

See **GRAPHITI_DEBUG_GUIDE.md** for detailed solutions:

1. **Solution 1**: Check if Graphiti's OpenAIClient accepts explicit API version parameter
2. **Solution 2**: Create custom Azure OpenAI client wrapper that ensures version is used
3. **Solution 3**: Add explicit headers to AsyncAzureOpenAI client

## Files to Reference

| File | Purpose |
|------|---------|
| `src/agent.py` lines 312-326 | Episode creation call |
| `src/graphiti_client.py` lines 78-120 | Episode processing |
| `src/graphiti_client.py` lines 38-76 | Graphiti initialization (has the issue) |
| `EPISODE_STRUCTURE.md` | Full architectural breakdown |
| `EPISODE_VISUAL_GUIDE.md` | Visual diagrams & examples |
| `GRAPHITI_DEBUG_GUIDE.md` | Debugging approach & solutions |

## Testing Episode Creation

```python
from src.agent import SyncMemoryAgent
from src.logging_config import setup_logging

setup_logging(log_level="DEBUG")

agent = SyncMemoryAgent(user_id="test")

# This creates an episode
response = agent.process_message("What is Python?")

# Check logs for success:
# ✅ "Conversation episode stored in knowledge graph" = SUCCESS
# ❌ "Could not store episode in knowledge graph" = FAILED

agent.close()
```

## Bottom Line

Episodes are just **structured containers for conversation turns**:
- Package user question + agent answer
- Add metadata (who, when, from where)
- Send to Graphiti for processing
- Get back searchable knowledge in Neo4j

The architecture is **sound and production-ready**. Just need to fix the API version configuration issue so Graphiti can use Azure OpenAI's Responses API for entity extraction.

See **GRAPHITI_DEBUG_GUIDE.md** for step-by-step fix approach! 🔧
