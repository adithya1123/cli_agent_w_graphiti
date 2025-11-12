# Agent Usage Guide

## Quick Start

### Prerequisites
- ✅ Neo4j running: `docker-compose ps` should show `neo4j` as "healthy"
- ✅ `.env` configured with API keys
- ✅ Dependencies installed: `uv sync`

### Start Using

**Option 1: Interactive CLI (Recommended for first time)**
```bash
uv run python main.py
```

**Option 2: Quick Demo**
```bash
uv run python quick_demo.py
```

**Option 3: Python Script**
```python
from src.agent import SyncMemoryAgent

agent = SyncMemoryAgent(user_id="my_session")
response = agent.process_message("Your message here")
print(response)
agent.close()
```

## Understanding the Output

### Logging Levels

The agent logs information at different levels:

**INFO** (default) - High-level operations:
```
2025-11-11 19:45:32 - agent.agent - INFO - Agent initialized for user: my_user
2025-11-11 19:45:33 - agent.tools - INFO - Executing web search with query: Claude AI
```

**DEBUG** - Detailed operations (use `setup_logging(log_level="DEBUG")`):
```
2025-11-11 19:45:34 - agent.agent - DEBUG - Retrieved 250 characters of context from memory
2025-11-11 19:45:35 - agent.tools - DEBUG - Web search returned 5 results
```

**WARNING** - Non-critical issues:
```
2025-11-11 19:45:36 - agent.agent - WARNING - Could not store episode in knowledge graph
```

**ERROR** - Critical issues:
```
2025-11-11 19:45:37 - agent.agent - ERROR - Failed to initialize Azure OpenAI client
```

### Example Session Walkthrough

```
===== CLI Starts =====
Welcome to the Memory Agent
Available commands: type 'help' for more info

===== User Input =====
You: What is Python?

===== Agent Processing (with logging) =====
[Logs show: Retrieving memory context...]
[Logs show: Getting AI response from Azure...]
[Logs show: Executing web search...]
[Logs show: Conversation episode stored in memory...]

===== Agent Response =====
Agent: Python is a high-level programming language...

===== Next Turn =====
You: Tell me more about data science
[Agent already has context from previous conversation]
```

## Features Explained

### 1. Web Search
When the agent needs current information, it automatically searches the web:
```
You: What are the latest AI developments in 2025?
[Agent searches web]
Agent: Based on recent developments...
```

### 2. Memory (Temporal Knowledge Graph)
The agent learns from your conversation:
```
You: I work with Python and JavaScript
You: What languages should I learn next?
[Agent remembers your previous statement]
Agent: Based on your experience with Python and JavaScript...
```

### 3. Multi-turn Conversations
The agent maintains context across multiple messages:
```
You: I'm interested in web development
You: What framework would you recommend?
[Agent remembers context from first message]
```

### 4. User Isolation
Each user has separate memory (via group_id):
```python
user1_agent = SyncMemoryAgent(user_id="user1")  # Separate memory
user2_agent = SyncMemoryAgent(user_id="user2")  # Different memory
```

## Troubleshooting

### Issue: "Connection error: Could not reach Azure OpenAI service"
**Solution:**
- Check internet connection
- Verify AZURE_OPENAI_API_ENDPOINT in .env
- Agent will auto-retry (wait a moment)

### Issue: "Deployment not found"
**Solution:**
- Update AZURE_OPENAI_CHAT_DEPLOYMENT_NAME to match your Azure resource
- Check Azure Portal for correct deployment name

### Issue: "Memory system initialization failed"
**Solution:**
- Ensure Neo4j is running: `docker-compose ps`
- Check NEO4J_PASSWORD in .env matches docker-compose.yml
- Neo4j logs: `docker-compose logs neo4j`

### Issue: Web search returns no results
**Solution:**
- This is normal - Tavily API returns no results for some queries
- Agent will still respond based on its training data
- Check TAVILY_API_KEY is valid

### Issue: Nothing appearing on screen
**Solution:**
- Agent is processing (this can take 5-10 seconds for first call)
- Check logs file: `logs/agent.log`
- Run with DEBUG logging:

```python
from src.logging_config import setup_logging
setup_logging(log_level="DEBUG")
```

## Best Practices

### 1. Always Close the Agent
```python
agent = SyncMemoryAgent(user_id="session")
try:
    response = agent.process_message("Hi")
finally:
    agent.close()  # Ensures cleanup
```

### 2. Reuse Agent Instance
```python
agent = SyncMemoryAgent(user_id="session")
response1 = agent.process_message("First question")
response2 = agent.process_message("Follow up")  # Context carried over
agent.close()
```

### 3. Use Context Manager
```python
with SyncMemoryAgent(user_id="session") as agent:
    response = agent.process_message("Hi")
    # Auto closes
```

### 4. Clear History When Needed
```python
agent = SyncMemoryAgent(user_id="session")
agent.process_message("First conversation")
agent.clear_history()  # Clears local history
agent.process_message("New conversation")  # Different context
```

## Advanced Usage

### Enable Debug Logging
```python
from src.logging_config import setup_logging
setup_logging(log_level="DEBUG", log_file="agent_debug.log")

agent = SyncMemoryAgent(user_id="debug_session")
response = agent.process_message("Test")
```

### Check Available Tools
```python
agent = SyncMemoryAgent(user_id="check_tools")
tools = agent._async_agent.tools.list_tools()
print(f"Available tools: {tools}")
```

### Access Memory System Status
```python
agent = SyncMemoryAgent(user_id="check_memory")
if agent._async_agent.memory_available:
    print("✅ Memory system is available")
else:
    print("⚠️ Memory system unavailable, agent will work without memory")
```

## Understanding Agent Capabilities

### What the Agent Can Do ✅
- Answer questions based on training data
- Search the web for current information
- Remember facts from conversation history
- Maintain multi-turn conversations
- Choose when to search the web automatically

### What the Agent Cannot Do ❌
- Make decisions outside conversation (no autonomous actions)
- Access private databases (only Neo4j for conversation memory)
- Execute code
- Make API calls other than Azure OpenAI, Tavily, Neo4j
- Access the internet directly (only through Tavily API)

## Performance Tips

1. **First call is slower** (~5-10 seconds)
   - Azure OpenAI initialization, Neo4j connection
   - Subsequent calls are faster (~2-3 seconds)

2. **Longer conversations use more tokens**
   - Agent keeps last 10 messages in context
   - Use `clear_history()` if you notice slowdown

3. **Web search adds latency** (~3-5 seconds extra)
   - Agent decides when to search automatically
   - You can't force/disable search

4. **Memory lookup is usually fast** (<1 second)
   - Unless Neo4j is slow or has connection issues

## Next Steps

1. **Try the CLI**: `uv run python main.py`
2. **Run the demo**: `uv run python quick_demo.py`
3. **Check logging**: Look for `logs/agent.log` after running
4. **Test web search**: Ask about current events or recent technology
5. **Test memory**: Ask follow-up questions about previous topics

Happy exploring! 🚀
