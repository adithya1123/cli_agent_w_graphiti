# Graphiti Integration Debug Guide

## The Problem

When `add_episode()` is called, Graphiti tries to extract entities using Azure OpenAI's LLM. This extraction requires the **Responses API** (structured output feature).

### Error Message
```
Error in generating LLM response: Error code: 400 -
{'error': {'code': 'BadRequest', 'message':
'Azure OpenAI Responses API is enabled only for api-version 2025-03-01-preview and later'}}
```

### What This Means
- Graphiti's LLM client is not properly using the correct API version
- The Azure OpenAI client is being created with the right version
- But somewhere in the chain, the version isn't being passed to the actual API call

## The Code Chain

### 1. **Agent Side** (src/agent.py)
```python
# ✅ This is correct - memory_client is initialized
await self.memory_client.add_episode(
    name=f"conversation_{datetime.now().isoformat()}",
    episode_body=episode_body,
    source="agent_conversation",
    source_description=f"Conversation turn between user and {self.agent_config.name}",
    reference_time=datetime.now(),
    group_id=self.user_id,
)
```

### 2. **GraphitiMemoryClient.add_episode()** (src/graphiti_client.py:78-120)
```python
async def add_episode(self, ...):
    # ... validation code ...

    kwargs = {
        "name": name,
        "episode_body": episode_body,
        "source": source_enum,
        "source_description": source_description,
        "reference_time": reference_time,
    }
    if group_id:
        kwargs["group_id"] = group_id

    # ✅ This calls Graphiti with correct parameters
    await self._graphiti.add_episode(**kwargs)
```

### 3. **Graphiti Initialization** (src/graphiti_client.py:38-76)
```python
async def initialize(self) -> None:
    # Create Azure client
    llm_azure_client = AsyncAzureOpenAI(
        api_key=self.config.api_key,
        api_version=self.config.api_version,  # 2025-03-01-preview ✅
        azure_endpoint=self.config.api_endpoint,
    )

    # Initialize LLM client for Graphiti
    self._llm_client = OpenAIClient(client=llm_azure_client)  # ⚠️ ISSUE HERE?

    # Create Graphiti instance
    self._graphiti = Graphiti(
        uri=self.neo4j_config.uri,
        user=self.neo4j_config.user,
        password=self.neo4j_config.password,
        llm_client=self._llm_client,  # Passes client to Graphiti
        embedder=embedder,
        cross_encoder=None,
    )
```

### 4. **Where Graphiti Fails**
Inside Graphiti's `add_episode()` method:
```
Graphiti.add_episode()
    └─→ extract_nodes()
        └─→ llm_client.generate_response()
            └─→ Creates request to Azure OpenAI
                └─→ FAILS: Wrong API version!
```

## Root Cause Analysis

### The Question
When Graphiti's `OpenAIClient` wraps our Azure client and makes LLM calls, does it:

1. ✅ Properly inherit the `api_version` from the wrapped Azure client?
2. ❌ Lose the `api_version` somewhere in the wrapping?
3. ❌ Have its own hardcoded api_version?
4. ❌ Not set proper headers for Responses API?

### What We Know
- Our AsyncAzureOpenAI is created with correct version: `2025-03-01-preview`
- Graphiti receives our llm_client: `OpenAIClient(client=llm_azure_client)`
- Error suggests version is NOT being passed to actual API call

## Solutions to Try

### Solution 1: Check LLMConfig Parameters
Graphiti's `OpenAIClient` might need explicit configuration:

**Current Code (Line 55):**
```python
self._llm_client = OpenAIClient(client=llm_azure_client)
```

**Try This:**
```python
# Option A: Check if OpenAIClient accepts additional parameters
from graphiti_core.llm_client import LLMConfig, OpenAIClient

# Create config with explicit API version
llm_config = LLMConfig(
    api_version=self.config.api_version,  # Pass explicitly
    api_key=self.config.api_key,
)

self._llm_client = OpenAIClient(
    client=llm_azure_client,
    config=llm_config,  # If supported
)
```

### Solution 2: Create Custom Azure OpenAI LLM Client
If Graphiti's OpenAIClient doesn't properly support Azure OpenAI with Responses API:

```python
# Create a custom wrapper that ensures API version is used
class AzureOpenAILLMClient:
    """Custom LLM client that properly handles Azure OpenAI Responses API"""

    def __init__(self, azure_client, api_version):
        self.client = azure_client
        self.api_version = api_version

    async def generate_response(self, messages, **kwargs):
        # Ensure api_version is set in request
        kwargs['api_version'] = self.api_version
        return await self.client.chat.completions.create(
            messages=messages,
            api_version=self.api_version,
            **kwargs
        )

# Use it:
self._llm_client = AzureOpenAILLMClient(
    llm_azure_client,
    self.config.api_version
)
```

### Solution 3: Verify Azure Client Headers
Check if Azure client needs explicit Responses API header:

```python
# Add headers that enable Responses API
llm_azure_client = AsyncAzureOpenAI(
    api_key=self.config.api_key,
    api_version=self.config.api_version,
    azure_endpoint=self.config.api_endpoint,
    # Try adding these headers:
    default_headers={
        "X-Azure-API-Version": self.config.api_version,
        "Accept": "application/json",
    }
)
```

## Investigation Steps

### Step 1: Check Graphiti's OpenAIClient
```bash
# Look at what OpenAIClient accepts
python -c "
from graphiti_core.llm_client import OpenAIClient
import inspect
print(inspect.signature(OpenAIClient.__init__))
"
```

Expected output shows what parameters it accepts.

### Step 2: Check What Graphiti Sends
Add debugging to see what API version Graphiti is using:

```python
# In src/graphiti_client.py, after initializing Graphiti:
import logging
logging.basicConfig(level=logging.DEBUG)

# This will show all HTTP requests to Azure OpenAI
# Look for: api-version=... in the URL
```

### Step 3: Test with Simplified Version
Create minimal test:

```python
# test_graphiti_minimal.py
import asyncio
from src.graphiti_client import GraphitiMemoryClient

async def test():
    client = GraphitiMemoryClient()
    await client.initialize()

    try:
        await client.add_episode(
            name="test_episode",
            episode_body="User: Hi\nAgent: Hello",
            source="text",
            source_description="Test",
            group_id="test_user"
        )
        print("✅ Episode stored successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"Type: {type(e).__name__}")

asyncio.run(test())
```

## Expected Behavior After Fix

### Before Fix
```
Calling add_episode()
    └─→ Error: Azure OpenAI Responses API version requirement
```

### After Fix
```
Calling add_episode()
    └─→ Azure OpenAI extracts entities (with Responses API)
    └─→ Graphiti creates relationships
    └─→ Neo4j stores episode
    ✅ Episode stored in knowledge graph
```

## Debugging Checklist

- [ ] Check Graphiti's OpenAIClient source code
- [ ] Verify AsyncAzureOpenAI has `api_version` property
- [ ] Check if Responses API requires special headers
- [ ] Test with minimal code (test_graphiti_minimal.py)
- [ ] Add logging to see actual API calls
- [ ] Check Azure portal for API usage logs
- [ ] Verify deployment supports Responses API (usually newer models)

## Key Files to Check

| File | Section | Issue |
|------|---------|-------|
| `src/graphiti_client.py` | Line 55 | OpenAIClient initialization |
| `src/graphiti_client.py` | Line 41-44 | AsyncAzureOpenAI creation |
| `src/graphiti_client.py` | Line 69-76 | Graphiti initialization |
| `.env` | Line 3 | Verify AZURE_OPENAI_API_VERSION |

## Success Indicators

When fixed, you should see:
```
2025-11-11 19:55:49 - agent.src.graphiti_client - DEBUG - Conversation episode stored in knowledge graph
```

Instead of:
```
2025-11-11 19:55:49 - Error: Azure OpenAI Responses API is enabled only for api-version...
```

## Resources

- [Graphiti GitHub](https://github.com/zep-ai/graphiti)
- [Azure OpenAI Responses API](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/json-mode)
- [Structured Output with Responses API](https://platform.openai.com/docs/guides/structured-outputs)

## Next Actions

1. **First**: Run Step 1 (check OpenAIClient signature)
2. **Second**: Run Step 2 (debug logging)
3. **Third**: Try Solution 1 or Solution 3
4. **Fourth**: If still failing, implement Solution 2 (custom client)
5. **Finally**: Test with test_graphiti_minimal.py

The architecture is correct - this is just a configuration/API usage issue! 🔧
