# Contracts: main
_Last updated: 2026-04-25_
_Covers: `main.py`_

---

## main()

**Summary**: CLI entry point — validates config, prompts for user, runs command dispatch loop.
**File**: `main.py:59`

**Side effects**:
- Calls `validate_all_configs()` — raises `ValueError` and exits with code 1 on missing env vars
- Calls `UserSessionManager.prompt_for_user()` — interactive, reads stdin
- Instantiates `SyncMemoryAgent` — blocks until Graphiti is initialized
- On `sys.exit(1)`: prints error message suggesting `docker-compose up -d`

**Failure modes**:
- `ValueError` from config validation → prints error, `sys.exit(1)`
- Any other exception during init → prints error with Docker hint, `sys.exit(1)`

---

## Command dispatch order

Commands are checked with `str.lower().startswith()` in this order:
1. `exit` / `quit`
2. `whoami`
3. `switch`
4. `users`
5. `delete user <id>`
6. `visualize [7|30|all]`
7. `clear`
8. `help`
9. _(anything else)_ → `agent.process_message()`

**Non-obvious behavior**:
- `delete user` requires confirmation input (`y` to proceed) — sends `EOFError` if stdin is closed
- `switch` calls `agent.close()` before re-initializing — the old agent's resources are always cleaned up
- If the user deletes their own account, the CLI automatically prompts for a new user and re-initializes

→ See also: `playbooks/add_cli_command.md`, `contracts/agent.md`, `contracts/user_session.md`
