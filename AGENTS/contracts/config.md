# Contracts: config
_Last updated: 2026-04-25_
_Covers: `src/config.py`_

---

## Module-level behavior

**Summary**: Calls `load_dotenv()` at import time, reading `.env` from the project root.
**File**: `src/config.py:8`

**Env dependencies**: Reads from `.env` at `<project_root>/.env` on every import.

**Non-obvious behavior**: All config values are read at import time (class-level `os.getenv()` calls). Changing env vars after import has no effect — restart the process.

---

## OpenAIConfig

**File**: `src/config.py:12`

| Attribute | Env var | Default | Required |
|-----------|---------|---------|---------|
| `api_key` | `OPENAI_API_KEY` | — | Yes |
| `api_endpoint` | `OPENAI_API_ENDPOINT` | `""` | No (empty = openai.com) |
| `chat_model` | `OPENAI_CHAT_MODEL` | `"gpt-4o"` | No |
| `embedding_api_key` | `OPENAI_EMBEDDING_API_KEY` | `""` | No (falls back to `api_key`) |
| `embedding_endpoint` | `OPENAI_EMBEDDING_ENDPOINT` | `""` | No |
| `embedding_model` | `OPENAI_EMBEDDING_MODEL` | `"text-embedding-3-small"` | No |
| `graphiti_llm_model` | `GRAPHITI_LLM_MODEL` | `""` | No (falls back to `chat_model`) |

**Non-obvious behavior**:
- `api_endpoint` non-empty → passed as `base_url` to `AsyncOpenAI`. Use Azure full endpoint format: `https://<resource>.cognitiveservices.azure.com/openai/v1/`
- `embedding_api_key` empty → `graphiti_client` falls back to `api_key` for embeddings
- `graphiti_llm_model` empty → `graphiti_client` uses `chat_model` for Graphiti's entity extraction

**Failure modes**: `validate()` raises `ValueError("OPENAI_API_KEY not set in environment")` if `api_key` is falsy.

---

## Neo4jConfig

**File**: `src/config.py:35`

| Attribute | Env var | Default |
|-----------|---------|---------|
| `uri` | `NEO4J_URI` | `"bolt://localhost:7687"` |
| `user` | `NEO4J_USER` | `"neo4j"` |
| `password` | `NEO4J_PASSWORD` | `"password"` |

---

## TavilyConfig

**File**: `src/config.py:48`

| Attribute | Env var | Required |
|-----------|---------|---------|
| `api_key` | `TAVILY_API_KEY` | Yes |

**Failure modes**: `validate()` raises `ValueError("TAVILY_API_KEY not set in environment")` if missing.

---

## validate_all_configs

**Summary**: Calls `validate()` on all config classes — raises `ValueError` on first missing required var.
**File**: `src/config.py:65`

**Consumed by**: `main()` in `main.py` — called before any other initialization.

→ See also: `playbooks/add_config_var.md`
