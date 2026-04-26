# Playbook: Add a CLI Command
_Last updated: 2026-04-25_

## Steps

1. **Add the command handler block in `main.py`**

   Open `main.py`. Find the `while True` loop. Add a new `if` block **before** the final `else` (message processing). Use `startswith()` for commands with arguments, `==` for exact matches:

   ```python
   if user_input.lower() == "mycommand":
       try:
           result = agent.some_method()
           print(f"Result: {result}\n")
       except Exception as e:
           logger.error(f"Error running mycommand: {e}", exc_info=True)
           print(f"Error: {e}\n")
       continue
   ```

2. **Add a method to `SyncMemoryAgent` (if needed)**

   If the command needs to call the memory client, add a sync wrapper method to `SyncMemoryAgent` in `src/agent.py`:

   ```python
   def some_method(self) -> ...:
       return self._loop.run_until_complete(
           self._async_agent.memory_client.some_async_method()
       )
   ```

3. **Add the underlying async method to `GraphitiMemoryClient` (if needed)**

   If new Neo4j/Graphiti logic is required, add an async method to `GraphitiMemoryClient` in `src/graphiti_client.py`. Guard with the standard check:

   ```python
   async def some_async_method(self) -> ...:
       if not self._graphiti:
           raise RuntimeError("Graphiti not initialized. Call initialize() first.")
       # ... implementation
   ```

4. **Update `print_welcome()` and `print_help()` in `main.py`**

   Add a line for the new command in both functions so users can discover it.

## Validation

Run `python main.py`, type the new command, and verify expected output.

## Common failures

**`AttributeError: 'SyncMemoryAgent' object has no attribute 'some_method'`**: You added the handler in `main.py` but forgot to add the wrapper method in `SyncMemoryAgent`.

**Command not reached / falls through to `process_message()`**: Your `if` block is after the final `else`. Move it before.

→ See also: `contracts/main.md`, `contracts/agent.md`, `contracts/graphiti_client.md`
