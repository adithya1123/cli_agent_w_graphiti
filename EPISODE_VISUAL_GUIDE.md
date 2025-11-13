# Episode Structure - Visual Guide

## Quick Reference: What Gets Stored

```
┌─────────────────────────────────────────────────────────────┐
│                    CONVERSATION TURN                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
         ┌────────────────────────────────┐
         │  User: "What is Python?"       │
         │  Agent: "Python is a...        │
         └────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                  EPISODE CREATED                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  name: "conversation_2025-11-11T19:55:49.123456"           │
│  ├─ Timestamp in ISO format                                 │
│  ├─ Unique per conversation turn                            │
│                                                               │
│  episode_body: "User: What is Python?\nAgent: Python is..." │
│  ├─ Full conversation content                               │
│  ├─ Used for entity extraction                              │
│  ├─ Stored for retrieval context                            │
│                                                               │
│  source: EpisodeType.text                                   │
│  ├─ Format type (text, json, markdown)                      │
│  ├─ Default: text for conversations                         │
│                                                               │
│  source_description: "Conversation turn between user..."    │
│  ├─ Human-readable context                                  │
│  ├─ Helps understand origin of data                         │
│                                                               │
│  reference_time: 2025-11-11 19:55:49.123456                │
│  ├─ When the conversation occurred                          │
│  ├─ Defaults to current time if not provided                │
│  ├─ Used for temporal ordering                              │
│                                                               │
│  group_id: "demo_user"                                      │
│  ├─ User isolation key                                      │
│  ├─ Each user has separate memory                           │
│  ├─ Filters searches to user-specific data                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              GRAPHITI PROCESSING                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Entity Extraction (via Azure OpenAI)                    │
│     ┌─────────────────────────────────────────┐             │
│     │ Input: "User: What is Python?..."       │             │
│     │                                          │             │
│     │ LLM identifies:                          │             │
│     │   • Python (entity)                      │             │
│     │   • programming language (type)          │             │
│     │   • question, answer (relationships)     │             │
│     └─────────────────────────────────────────┘             │
│                                                               │
│  2. Relationship Creation                                   │
│     Python ──[is_a]─→ programming_language                  │
│     Python ──[mentioned_in]─→ Episode                       │
│                                                               │
│  3. Temporal Marking                                        │
│     valid_at: 2025-11-11 19:55:49                          │
│     created_at: 2025-11-11 19:55:49                        │
│     invalid_at: NULL (still valid)                          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              NEO4J STORAGE                                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Nodes:                                                      │
│  ├─ Episode                                                  │
│  │  └─ uuid, name, group_id, content, source               │
│  ├─ Entity (Python)                                         │
│  │  └─ name, type, attributes                               │
│  └─ Community                                                │
│     └─ Related concepts                                      │
│                                                               │
│  Edges:                                                      │
│  ├─ Episode -[RELATES_TO]→ Entity                           │
│  │  └─ with temporal data                                   │
│  └─ Entity -[RELATES_TO]→ Entity                            │
│     └─ relationships                                         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│         SEARCHABLE KNOWLEDGE GRAPH                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  User searches: "Tell me about programming"                 │
│          ↓                                                    │
│  Graphiti searches Neo4j:                                    │
│    ├─ Find: Python (programming language entity)            │
│    ├─ Filter: group_id = "demo_user"                       │
│    ├─ Order: valid_at DESC (newest first)                  │
│    └─ Return: "Python is a high-level prog language..."     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Episode Parameters Explained

### 1. **name**
```python
name=f"conversation_{datetime.now().isoformat()}"
# Example: "conversation_2025-11-11T19:55:49.123456"

Why?
  • Unique per episode
  • Sortable (ISO format)
  • Readable (includes timestamp)
  • No duplicates possible
```

### 2. **episode_body**
```python
episode_body = f"User: {user_message}\nAgent: {final_response}"
# Example:
# "User: What is Python?
#  Agent: Python is a high-level programming language..."

Why?
  • Full context for extraction
  • Both question and answer
  • Preserves conversation flow
  • More information = better entity extraction
```

### 3. **source**
```python
source="agent_conversation"  # String
    ↓
source_enum = EpisodeType.text  # Converted to enum

Options:
  • "text" → EpisodeType.text (default, for conversations)
  • "json" → EpisodeType.json (for structured data)
  • "md" / "markdown" → EpisodeType.md (for markdown docs)

Why enum?
  • Graphiti requires enum, not string
  • Type safety
  • Clear valid options
```

### 4. **source_description**
```python
source_description="Conversation turn between user and Knowledge Graph Agent"

Why?
  • Human-readable context
  • Explains where data came from
  • Helpful in logs and debugging
  • Auto-defaults if not provided
```

### 5. **reference_time**
```python
reference_time=datetime.now()

Why?
  • Temporal tracking
  • Enables time-based queries ("facts from last week")
  • Ordered retrieval (newest first)
  • Auto-defaults to now() if not provided
```

### 6. **group_id**
```python
group_id=self.user_id  # "demo_user", "user1", etc.

Why?
  • Multi-user support
  • User isolation (don't leak data between users)
  • Filters searches to user's own memories
  • Enables privacy

Example:
  User1 asks about Python
  User2 asks about Java

  When User1 searches "programming":
    ✓ Gets: Python facts (their conversation)
    ✗ Doesn't get: Java facts (other user's data)
```

## Code Flow: From User Message to Episode

```python
# 1. USER ASKS QUESTION
user_input = "What is Python?"

# 2. AGENT PROCESSES
response = "Python is a high-level programming language..."
conversation_history = [
    {"role": "user", "content": "What is Python?"},
    {"role": "assistant", "content": "Python is..."}
]

# 3. BUILD EPISODE
episode_body = f"User: What is Python?\nAgent: Python is..."
episode_name = f"conversation_2025-11-11T19:55:49.123456"

# 4. ADD TO KNOWLEDGE GRAPH
await self.memory_client.add_episode(
    name=episode_name,           # conversation_2025-11-11T19:55:49.123456
    episode_body=episode_body,   # Full Q&A
    source="agent_conversation", # What type
    source_description="Conversation turn...",  # Why/where
    reference_time=datetime.now(),  # When
    group_id=self.user_id        # For whom
)

# 5. GRAPHITI PROCESSES
#    ├─ Extracts: "Python", "programming language"
#    ├─ Creates: Nodes, edges, relationships
#    └─ Stores: In Neo4j with temporal info

# 6. MEMORY READY
#    Now if user asks "Tell me about programming"
#    Graphiti can search and find this Python fact!
```

## What Gets Stored vs Not Stored

### ✅ STORED (In Episode)
- Full conversation text (both user and agent)
- Timestamp of conversation
- User ID (for isolation)
- Source metadata
- Everything needed for extraction and retrieval

### ❌ NOT STORED (In Episode)
- Internal agent state
- Tool call details (web search queries)
- Internal reasoning
- Configuration parameters
- Conversation history (stored separately in memory)

### 🔄 PROCESSED BY GRAPHITI (Not in raw episode)
- Extracted entities (Python → Entity node)
- Relationships (Python → programming language)
- Temporal validity (when is fact true)
- Communities (related concepts)

## Episode in Neo4j

```
MATCH (e:Episodic)-[r:RELATES_TO]-(ent:Entity)
WHERE e.group_id = "demo_user"
RETURN e, r, ent

Results:
┌──────────────────────────────────────┐
│ Episodic                             │
├──────────────────────────────────────┤
│ uuid: "abc-123"                      │
│ name: "conversation_2025-11-11..."   │
│ group_id: "demo_user"                │
│ created_at: 2025-11-11 19:55:49      │
│ valid_at: 2025-11-11 19:55:49        │
│ content: "User: What is Python?..."  │
│ source: "agent_conversation"         │
└──────────────────────────────────────┘
           │
        [RELATES_TO]
           │
           ↓
┌──────────────────────────────────────┐
│ Entity                               │
├──────────────────────────────────────┤
│ uuid: "xyz-789"                      │
│ name: "Python"                       │
│ type: "programming_language"         │
│ created_at: 2025-11-11 19:55:49      │
└──────────────────────────────────────┘
```

## Summary Table

| Component | Type | Example | Purpose |
|-----------|------|---------|---------|
| **name** | str | conversation_2025-11-11T19:55:49 | Unique ID |
| **episode_body** | str | User: What is...Agent: Python is... | Content to extract |
| **source** | enum | EpisodeType.text | Format type |
| **source_description** | str | Conversation turn between... | Context |
| **reference_time** | datetime | 2025-11-11 19:55:49 | Temporal info |
| **group_id** | str | demo_user | User isolation |

This is everything needed to capture a conversation turn and store it as searchable knowledge! 🧠
