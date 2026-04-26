# Playbook: Add a New Agent Tool
_Last updated: 2026-04-25_

## Steps

1. **Add the tool implementation in `src/tools.py`**

   Add a new method to `ToolRegistry` or a new tool class:

   ```python
   class MyNewTool:
       def __init__(self):
           # initialize client / config here
           pass

       def run(self, param: str) -> str:
           # tool logic — must return a string
           return result_string
   ```

   Then register it in `ToolRegistry.__init__`:

   ```python
   self.my_tool = MyNewTool()
   self.tools = {
       "web_search": self.web_search.search_and_format,
       "my_new_tool": self.my_tool.run,   # add here
   }
   ```

2. **Add the OpenAI tool schema in `src/agent.py`**

   In `MemoryAgent._get_tool_definitions()`, add a new entry to the `self._tool_definitions` list:

   ```python
   {
       "type": "function",
       "function": {
           "name": "my_new_tool",
           "description": "...",
           "parameters": {
               "type": "object",
               "properties": {
                   "param": {"type": "string", "description": "..."}
               },
               "required": ["param"],
           },
       },
   }
   ```

3. **Handle the tool name in `MemoryAgent._execute_tool_call()`**

   In `src/agent.py`, add an `elif` block in `_execute_tool_call()`:

   ```python
   elif tool_name == "my_new_tool":
       param = tool_args.get("param", "")
       try:
           return await asyncio.wait_for(
               asyncio.to_thread(self.tools.call_tool, "my_new_tool", param=param),
               timeout=30.0,
           )
       except asyncio.TimeoutError:
           return "Tool timed out."
       except Exception as e:
           return f"Tool error: {str(e)}"
   ```

4. **Add required config (if needed)**

   If the tool needs an API key, add a new config class to `src/config.py` following the existing pattern, add it to `validate_all_configs()`, and add the env var to `.env.example`.

## Validation

Run `python main.py` and send a message that should trigger the tool. Check logs for `"Executing ..."` or add a debug log. Verify the tool result appears in the response.

## Common failures

**Tool never invoked**: The LLM didn't decide to use it. Check the `description` field — it must clearly explain when to use the tool.

**`Unknown tool requested: my_new_tool`**: The name in `_get_tool_definitions()` doesn't match the name in `_execute_tool_call()`. They must be identical strings.

**`TypeError` in tool call**: Tool function signature doesn't match the kwargs passed in `call_tool()`.

→ See also: `contracts/tools.md`, `contracts/agent.md`
