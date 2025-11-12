# Episode Structure & Memory Storage Architecture

## Overview
Episodes are the fundamental unit of memory in Graphiti. Each conversation turn is stored as an episode that Graphiti processes to extract entities, relationships, and temporal information.

## Episode Creation Flow

### 1. **Entry Point** - Agent Message Processing
**File:** `src/agent.py:312-326`

```python
# Each time process_message() completes, it creates an episode
episode_body = f"User: {user_message}\nAgent: {final_response}"
await self.memory_client.add_episode(
    name=f"conversation_{datetime.now().isoformat()}",
    episode_body=episode_body,
    source="agent_conversation",
    source_description=f"Conversation turn between user and {self.agent_config.name}",
    reference_time=datetime.now(),
    group_id=self.user_id,  # User isolation
)
```

### 2. **Episode Data Structure**

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `name` | str | Unique episode identifier | `conversation_2025-11-11T19:55:49.123456` |
| `episode_body` | str | The actual content | `User: What is Python?\nAgent: Python is...` |
| `source` | EpisodeType | Content format type | `EpisodeType.text` |
| `source_description` | str | Human-readable source info | `Conversation turn between user and Knowledge Graph Agent` |
| `reference_time` | datetime | When the episode occurred | `datetime.now()` |
| `group_id` | str | User identifier for isolation | `my_user` |

### 3. **GraphitiMemoryClient Processing**
**File:** `src/graphiti_client.py:78-120`

```python
async def add_episode(
    self,
    name: str,                          # Unique episode ID
    episode_body: str,                  # Content to process
    source: str = "text",               # Format (text, json, md)
    source_description: Optional[str],  # Context about source
    reference_time: Optional[datetime], # Timestamp
    group_id: Optional[str] = None,    # User isolation
) -> None:
```

**Processing Steps:**

#### Step 3a: Parameter Validation
```python
if not self._graphiti:
    raise RuntimeError("Graphiti not initialized. Call initialize() first.")
```

#### Step 3b: Set Defaults
```python
if reference_time is None:
    reference_time = datetime.now()

if source_description is None:
    source_description = f"Episode from {source}"
```

#### Step 3c: Convert Source to Enum
```python
# Custom EpisodeType enum (since Graphiti doesn't export it)
class EpisodeType(str, Enum):
    text = "text"
    json = "json"
    md = "md"

# Convert string source to enum
source_enum = EpisodeType.text  # Default
if source.lower() == "json":
    source_enum = EpisodeType.json
elif source.lower() == "md" or source.lower() == "markdown":
    source_enum = EpisodeType.md
```

#### Step 3d: Build kwargs Dictionary
```python
kwargs = {
    "name": name,
    "episode_body": episode_body,
    "source": source_enum,              # As enum, not string
    "source_description": source_description,
    "reference_time": reference_time,
}
if group_id:
    kwargs["group_id"] = group_id       # Only if provided
```

#### Step 3e: Send to Graphiti
```python
await self._graphiti.add_episode(**kwargs)
```

## Episode Processing by Graphiti

Once passed to Graphiti, the episode undergoes:

### 1. **Entity Extraction**
- Uses Azure OpenAI's LLM (with Responses API)
- Identifies named entities (people, concepts, etc.)
- Extracts attributes and relationships

### 2. **Temporal Tracking**
- Records `valid_at` (when entity became relevant)
- Records `invalid_at` (when entity stopped being relevant)
- Records `created_at` (when recorded in DB)

### 3. **Knowledge Graph Storage**
- Creates nodes in Neo4j for:
  - Episodes (Episodic nodes)
  - Entities mentioned (Entity nodes)
  - Communities of related entities (Community nodes)

- Creates relationships (RELATES_TO) with:
  - Temporal properties (valid_at, invalid_at, created_at)
  - Edge names (relationship types)

### 4. **User Isolation**
- `group_id` stored with episode
- Ensures different users' data remains separate
- Used in search queries to filter by user

## Example Episode Lifecycle

### Scenario: User asks about Python

```
TIME: 2025-11-11 19:55:49

1. USER MESSAGE
   "What is Python?"

2. AGENT RESPONSE
   "Python is a high-level programming language..."

3. EPISODE CREATED
   {
     name: "conversation_2025-11-11T19:55:49.123456",
     episode_body: "User: What is Python?\nAgent: Python is a high-level...",
     source: EpisodeType.text,
     source_description: "Conversation turn between user and Knowledge Graph Agent",
     reference_time: 2025-11-11 19:55:49,
     group_id: "demo_user"
   }

4. GRAPHITI PROCESSING
   ├─ Extracts entities: Python (programming language)
   ├─ Creates relationships: Python → programming language
   ├─ Stores with timestamp: valid_at=2025-11-11 19:55:49
   └─ Tags with group_id: "demo_user"

5. NEO4J STORAGE
   Neo4j Database:
   (Episode {
     uuid: "...",
     name: "conversation_2025-11-11T19:55:49.123456",
     group_id: "demo_user",
     created_at: 2025-11-11 19:55:49,
     valid_at: 2025-11-11 19:55:49,
     content: "User: What is Python?...",
     source: "agent_conversation"
   })

   (Entity {name: "Python", type: "programming language"})

   (Episode) -[RELATES_TO {name: "is_language"}]-> (Entity)

6. SEARCH & RETRIEVAL
   Next time user asks about programming:

   Query: "Tell me about programming"

   Graphiti searches Neo4j:
   ├─ Matches: Python (from previous episode)
   ├─ Filters by: group_id = "demo_user"
   ├─ Orders by: valid_at DESC (most recent first)
   └─ Returns: "Python is a high-level programming language..."
```

## Data Flow Diagram

```
Agent.process_message()
        ↓
   [Conversation Turn]
        ↓
episode_body = f"User: {msg}\nAgent: {response}"
        ↓
GraphitiMemoryClient.add_episode()
        ↓
   [Validate & Default]
        ↓
   [Convert source to enum]
        ↓
   [Build kwargs with group_id]
        ↓
await graphiti.add_episode(**kwargs)
        ↓
   [Azure OpenAI - Extract Entities]
        ↓
   [Neo4j - Store Episode & Entities]
        ↓
   [Temporal Relationships Created]
        ↓
[Searchable in Knowledge Graph]
```

## Key Implementation Details

### 1. **EpisodeType Custom Enum**
Why custom? Graphiti's EpisodeType isn't exported in public API
```python
class EpisodeType(str, Enum):
    """Since graphiti_core doesn't export EpisodeType"""
    text = "text"
    json = "json"
    md = "md"
```

### 2. **User Isolation via group_id**
Every episode tagged with `user_id`:
```python
group_id=self.user_id  # Different per user
```
Ensures multi-user system keeps data separate

### 3. **Async Architecture**
All episode operations are async:
```python
await self.memory_client.add_episode(...)  # Async call
```
Prevents blocking in event loop

### 4. **Error Handling**
Episode storage is non-critical:
```python
try:
    await self.memory_client.add_episode(...)
except Exception as e:
    logger.warning(f"Could not store episode: {e}")
    # Agent continues without memory
```

### 5. **Timestamp Management**
Automatic default to current time:
```python
if reference_time is None:
    reference_time = datetime.now()
```

## Current Issues & Debugging

### Issue: "Azure OpenAI Responses API is enabled only for api-version 2025-03-01-preview and later"

**Location:** When Graphiti tries to extract entities via Azure OpenAI

**Root Cause:** Graphiti's `OpenAIClient` may not be properly receiving/using the API version

**Code Location:** `src/graphiti_client.py` line 55
```python
self._llm_client = OpenAIClient(client=llm_azure_client)
# Need to verify: Does OpenAIClient properly use api_version from llm_azure_client?
```

**Investigation Needed:**
1. Check if Graphiti's OpenAIClient wraps the Azure client correctly
2. Verify Azure OpenAI headers are set with correct api-version
3. May need to pass api_version explicitly to OpenAIClient

## Testing Episode Creation

### Manual Test
```python
from src.agent import SyncMemoryAgent
from src.logging_config import setup_logging

setup_logging(log_level="DEBUG")

agent = SyncMemoryAgent(user_id="test_user")

# This creates an episode in memory
response = agent.process_message("What is Python?")

# Check logs for:
# - "Conversation episode stored in knowledge graph" (success)
# - "Could not store episode in knowledge graph" (memory issue)

agent.close()
```

### Expected Logs for Successful Episode Storage
```
2025-11-11 19:55:49 - agent.src.graphiti_client - DEBUG - Episode storage scheduled...
2025-11-11 19:55:50 - agent.src.agent - DEBUG - Conversation episode stored in knowledge graph
```

## Next Steps

1. **Debug Graphiti LLM Client**: Verify api_version propagation
2. **Test Episode Extraction**: Check if entities are properly extracted
3. **Verify Neo4j Storage**: Query database to see stored episodes
4. **Test Search**: Verify search returns stored episodes
5. **Test User Isolation**: Confirm different users have separate memories

## Summary

Episodes in our system:
- ✅ Built from conversation turns (user message + agent response)
- ✅ Include metadata (timestamps, source, user ID)
- ✅ Passed to Graphiti for processing
- ✅ Stored in Neo4j as temporal knowledge graph
- ⚠️ Entity extraction blocked by Azure OpenAI Responses API config issue
- ✅ Architecture correct, just needs configuration fix
