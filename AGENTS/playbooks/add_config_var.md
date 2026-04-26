# Playbook: Add a New Config Variable
_Last updated: 2026-04-25_

## Steps

1. **Add the attribute to the appropriate config class in `src/config.py`**

   ```python
   class MyServiceConfig:
       api_key: str = os.getenv("MY_SERVICE_API_KEY")
       timeout: int = int(os.getenv("MY_SERVICE_TIMEOUT", "30"))
   ```

   Or add to an existing class if it belongs there (e.g. `AgentConfig` for behavior tuning).

2. **Add `validate()` if the var is required**

   ```python
   @classmethod
   def validate(cls) -> None:
       if not cls.api_key:
           raise ValueError("MY_SERVICE_API_KEY not set in environment")
   ```

3. **Add to `validate_all_configs()` if required**

   ```python
   def validate_all_configs() -> None:
       OpenAIConfig.validate()
       Neo4jConfig.validate()
       TavilyConfig.validate()
       MyServiceConfig.validate()  # add here
   ```

4. **Add the var to `.env.example`** (if the file exists)

   Document the expected format and whether it's required or optional.

## Validation

Run `python main.py` without the env var set. If required, you should see a clear `ValueError` message. If optional, startup should succeed with the default value.

## Common failures

**Config reads old value after `.env` change**: Config is read at import time. Restart the process.

**`int()` conversion fails at import**: If `os.getenv("MY_VAR", "default")` returns a non-numeric string, the `int()` call fails at import (before `validate()` runs). Prefer `int(os.getenv(...) or "30")` to handle `None` explicitly.

→ See also: `contracts/config.md`
