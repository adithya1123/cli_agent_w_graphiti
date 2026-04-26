# Playbook: Tune Agent Behavior
_Last updated: 2026-04-25_

All tuning parameters are in `src/agent.py` and `src/config.py` / `.env`.

## Memory retrieval

| What to change | Where | Default |
|---------------|-------|---------|
| Number of memory results | `num_results=3` in `MemoryAgent.process_message()` | 3 |
| Memory context character cap | `context[:1200]` in `MemoryAgent.process_message()` | 1200 |
| Memory search timeout | `asyncio.wait_for(..., timeout=15.0)` in `process_message()` | 15s |

## LLM token budgets

| What to change | Where | Default |
|---------------|-------|---------|
| Routing call token budget | `max_completion_tokens=4000` in `_get_ai_response()` | 4000 |
| Synthesis call token budget | `max_completion_tokens=16000` in `_handle_tool_calls()` | 16000 |
| Conversation window | `CONVERSATION_HISTORY_LIMIT` env var | 10 |

> Do NOT lower the synthesis call below ~8000 for reasoning models — they consume tokens on internal reasoning steps and may return blank responses.

## Web search

| What to change | Where | Default |
|---------------|-------|---------|
| Number of search results | `max_results=3` in `_execute_tool_call()` | 3 |
| Per-result content cap | `content[:300]` in `tools.py format_search_results()` | 300 chars |
| Search timeout | `asyncio.wait_for(..., timeout=30.0)` in `_execute_tool_call()` | 30s |

## System prompt

Edit `MemoryAgent._create_system_prompt()` in `src/agent.py`. The prompt currently:
- Identifies the agent by `AGENT_NAME` env var
- Describes the two capabilities (knowledge graph memory + web search)
- Instructs the model to distinguish memory vs. web sources

## Episode storage retry

| What to change | Where | Default |
|---------------|-------|---------|
| Max retries | `max_retries = 3` in `_store_episode_background()` | 3 |
| Backoff delays | `delay = 2 ** attempt` (2s, 4s) | exponential |

## Validation

After changes, run `python main.py`, send a few messages, and watch for:
- Logs showing memory retrieval (`"Retrieved N characters of context"`)
- Logs showing episode storage (`"Conversation episode stored"`)
- No blank responses

→ See also: `contracts/agent.md`, `02_business_logic.md`
