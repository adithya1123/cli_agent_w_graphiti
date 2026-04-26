# Contracts: user_session
_Last updated: 2026-04-25_
_Covers: `src/user_session.py`_

---

## UserSessionManager.prompt_for_user

**Summary**: Interactive prompt — reads last user from disk, shows as default, validates and saves new input.
**File**: `src/user_session.py:56`

**Returns**: A validated user ID string.

**Side effects**:
- Creates `~/.agent_memory/` directory if absent
- Writes chosen user ID to `~/.agent_memory/last_user`

**Non-obvious behavior**:
- Loops indefinitely until a valid ID is entered — never returns an invalid ID
- Empty input + existing last_user → silently reuses last_user without prompting again

**Consumed by**: `main()` in `main.py` — at startup and after `switch` command

---

## UserSessionManager.validate_user_id

**Summary**: Validates user ID format.
**File**: `src/user_session.py:47`

**Returns**: `True` if matches `^[a-zA-Z0-9_\-]{1,50}$`, `False` otherwise.

**Non-obvious behavior**: This regex is also the implicit constraint on all `group_id` values in Neo4j. IDs outside this pattern should never reach the graph — enforce this upstream.

---

## UserSessionManager.get_last_user / save_user

**Summary**: Read/write `~/.agent_memory/last_user` as a plain text file.
**File**: `src/user_session.py:24`, `src/user_session.py:37`

**Non-obvious behavior**:
- `get_last_user()` returns `None` (not empty string) if file missing or empty
- Both methods swallow IO exceptions with a warning log — never raise

→ See also: `contracts/main.md`
