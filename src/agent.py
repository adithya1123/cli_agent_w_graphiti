"""Main agent implementation with memory, web search, and OpenAI function calling"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional
from openai import AsyncOpenAI, APIError, APIConnectionError

from src.config import OpenAIConfig, AgentConfig
from src.graphiti_client import GraphitiMemory
from src.tools import ToolRegistry
from src.logging_config import get_logger

logger = get_logger(__name__)

_ERROR_PREFIXES = (
    "Connection error:",
    "Authentication error:",
    "Rate limited:",
    "Deployment not found:",
    "API error:",
    "Error generating response:",
    "Error: Could not get response",
    "Error processing tool results:",
)


class MemoryAgent:
    """Agent with temporal knowledge graph memory and web search capabilities"""

    def __init__(self, user_id: Optional[str] = None, loop=None):
        """Initialize the agent with optional event loop"""
        from src.graphiti_client import GraphitiMemoryClient

        self.config = OpenAIConfig()
        self.agent_config = AgentConfig()

        # Initialize OpenAI client
        try:
            # Build client kwargs - include base_url if using Azure endpoint
            client_kwargs = {"api_key": self.config.api_key}
            if self.config.api_endpoint:
                client_kwargs["base_url"] = self.config.api_endpoint

            self.llm_client = AsyncOpenAI(**client_kwargs)
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)
            raise RuntimeError(f"Cannot initialize LLM client: {str(e)}")

        # Initialize async memory client (for use within async methods)
        self.memory_client = GraphitiMemoryClient()
        self.memory_available = False
        try:
            # Note: We don't initialize the async client here - it will be initialized when needed
            # This avoids blocking during __init__
            self.memory_available = True
            logger.info("Memory client configured successfully")
        except Exception as e:
            logger.warning(f"Memory system initialization failed: {e}. Agent will work without memory.", exc_info=True)
            self.memory_available = False

        # Initialize tools
        try:
            self.tools = ToolRegistry()
            logger.info(f"Tools initialized: {self.tools.list_tools()}")
        except Exception as e:
            logger.error(f"Failed to initialize tools: {e}", exc_info=True)
            raise RuntimeError(f"Cannot initialize tools: {str(e)}")

        # User ID for tracking conversations
        self.user_id = user_id or "default_user"

        # Conversation history for context window
        self.conversation_history: list[dict] = []

        logger.info(f"Agent initialized for user: {self.user_id}")

    def _get_tool_definitions(self) -> list:
        """Get OpenAI function calling tool definitions (built once, reused)"""
        if not hasattr(self, "_tool_definitions"):
            self._tool_definitions = [
                {
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "description": "Search the web for current information when you need up-to-date facts, news, prices, or information beyond your training data",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The search query to find relevant information on the web",
                                }
                            },
                            "required": ["query"],
                        },
                    },
                }
            ]
        return self._tool_definitions

    def _create_system_prompt(self) -> str:
        """Create the system prompt for the agent"""
        return f"""You are {self.agent_config.name}, a helpful AI assistant with access to:
1. A temporal knowledge graph that stores facts learned from past conversations
2. Web search capability for current information

Your approach:
- Use memories from past conversations when relevant
- Call web_search when you need current information, recent news, prices, or facts beyond your training
- Be clear about whether you're using past memories vs. current web information
- Learn and remember new information from conversations

You have access to the web_search function - use it intelligently when needed."""

    async def _get_ai_response(
        self, user_message: str, context: str = "", tools: Optional[list] = None
    ) -> dict:
        """
        Get response from Azure OpenAI with function calling support

        Returns:
            Dict with 'content' (str) and 'tool_calls' (list or None)
        """
        # Build messages for the API
        system_message = self._create_system_prompt()

        if context:
            system_message += f"\n\nContext from your memories:\n{context}"

        messages = [
            {"role": "system", "content": system_message},
        ]

        # Add conversation history (keep last N messages)
        history_limit = self.agent_config.conversation_history_limit
        for msg in self.conversation_history[-history_limit:]:
            messages.append(msg)

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Build request kwargs.
                # Routing call: only needs to decide whether to answer or call a tool.
                # 4000 tokens is sufficient — tool call JSON is tiny; direct answers are short.
                kwargs = {
                    "model": self.config.chat_model,
                    "messages": messages,
                    "max_completion_tokens": 4000,
                }

                # Add tools if provided
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"

                response = await self.llm_client.chat.completions.create(**kwargs)

                # Extract response content and tool calls
                message = response.choices[0].message
                logger.debug(
                    f"Initial LLM: finish_reason={response.choices[0].finish_reason!r}, "
                    f"content_len={len(message.content) if message.content else 0}, "
                    f"tool_calls={len(message.tool_calls) if message.tool_calls else 0}"
                )
                result = {
                    "content": message.content,
                    "tool_calls": message.tool_calls if hasattr(message, "tool_calls") else None,
                }

                return result

            except APIConnectionError as e:
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error(f"Connection error after {max_retries} retries: {e}", exc_info=True)
                    return {"content": "Connection error: Could not reach Azure OpenAI service", "tool_calls": None}
                logger.warning(f"Connection error (attempt {retry_count}/{max_retries}): {e}")

            except APIError as e:
                logger.error(f"API error from Azure OpenAI: {e}", exc_info=True)
                error_msg = str(e)
                if "401" in error_msg or "403" in error_msg:
                    return {"content": "Authentication error: Please check your API credentials", "tool_calls": None}
                elif "429" in error_msg:
                    return {"content": "Rate limited: Too many requests. Please wait a moment.", "tool_calls": None}
                elif "404" in error_msg:
                    return {"content": "Deployment not found: Please check your Azure deployment configuration", "tool_calls": None}
                return {"content": f"API error: {error_msg}", "tool_calls": None}

            except Exception as e:
                logger.error(f"Unexpected error getting AI response: {e}", exc_info=True)
                return {"content": f"Error generating response: {str(e)}", "tool_calls": None}

        return {"content": "Error: Could not get response after multiple attempts", "tool_calls": None}

    async def _execute_tool_call(self, tool_call) -> str:
        """Execute a single tool call and return the result"""
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)

        if tool_name == "web_search":
            query = tool_args.get("query", "")
            logger.info(f"Executing web search with query: {query}")
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(self.tools.call_tool, "web_search", query=query, max_results=3),
                    timeout=30.0,
                )
            except asyncio.TimeoutError:
                logger.warning(f"Web search timed out for query: {query}")
                return "Web search timed out. Please try again or rephrase your query."
            except Exception as e:
                logger.error(f"Web search failed: {e}", exc_info=True)
                return f"Web search error: {str(e)}"
        else:
            logger.warning(f"Unknown tool requested: {tool_name}")
            return f"Unknown tool: {tool_name}"

    async def _handle_tool_calls(self, tool_calls: list, messages: list) -> tuple[str, list]:
        """
        Handle tool calls from the LLM

        Returns:
            (final_response, updated_messages)
        """
        # Execute all tool calls in parallel
        results = await asyncio.gather(
            *[self._execute_tool_call(tc) for tc in tool_calls],
            return_exceptions=True,
        )
        for tool_call, tool_result in zip(tool_calls, results):
            if isinstance(tool_result, Exception):
                tool_result = f"Tool error: {tool_result}"
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": tool_call.function.name,
                    "content": tool_result,
                }
            )

        # Get final response from LLM with tool results.
        # Pass tool_choice="none" to FORCE a text response — prevents the model
        # from looping back into tool-call mode (which would return content=None).
        try:
            response = await self.llm_client.chat.completions.create(
                model=self.config.chat_model,
                messages=messages,
                max_completion_tokens=16000,
                tools=self._get_tool_definitions(),
                tool_choice="none",
            )

            message = response.choices[0].message
            logger.debug(
                f"Synthesis LLM: finish_reason={response.choices[0].finish_reason!r}, "
                f"content_len={len(message.content) if message.content else 0}, "
                f"has_tool_calls={bool(message.tool_calls)}"
            )
            final_content = message.content or "I processed the search results but was unable to generate a response. Please try again."
            return final_content, messages
        except Exception as e:
            logger.error(f"Error getting final response after tool calls: {e}", exc_info=True)
            return f"Error processing tool results: {str(e)}", messages

    async def process_message(self, user_message: str) -> str:
        """
        Process a user message with function calling support

        Args:
            user_message: The user's input message

        Returns:
            The agent's response
        """
        # Validate input
        if not user_message or not user_message.strip():
            return "Please provide a message."

        # Search memory for relevant context
        context = ""
        if self.memory_available:
            try:
                # Initialize memory client if needed (first time)
                if not self.memory_client._graphiti:
                    await self.memory_client.initialize()

                context = await asyncio.wait_for(
                    self.memory_client.get_context_for_query(
                        query=user_message,
                        user_id=self.user_id,
                        num_results=3,
                    ),
                    timeout=15.0,
                )
                # Cap context to avoid polluting the system prompt with stale/verbose memories
                if len(context) > 1200:
                    context = context[:1200] + "\n[...memories truncated]"
                logger.debug(f"Retrieved {len(context)} characters of context from memory")
            except asyncio.TimeoutError:
                logger.warning("Memory search timed out after 15s; continuing without context")
                context = ""
            except Exception as e:
                logger.warning(f"Failed to retrieve context from memory: {e}")
                context = ""  # Continue without context

        # Get initial response with tools available
        # This will populate the messages list and handle any tool calls
        ai_result = await self._get_ai_response(user_message, context, tools=self._get_tool_definitions())

        # Process tool calls if the LLM decided to use them
        final_response = ai_result["content"]
        if ai_result["tool_calls"]:
            # Build a lean message list for tool handling — no history needed.
            # The synthesis call only needs: system + current user turn + tool results.
            system_message = self._create_system_prompt()
            if context:
                system_message += f"\n\nContext from your memories:\n{context}"

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ]

            # Add the assistant response with tool calls
            messages.append({
                "role": "assistant",
                "content": ai_result["content"] or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in ai_result["tool_calls"]
                ]
            })

            # Handle tool calls
            final_response, _ = await self._handle_tool_calls(ai_result["tool_calls"], messages)

        # Ensure we always have a string response
        if not final_response:
            final_response = "I was unable to generate a response. Please try again."

        # Add to conversation history (skip if response is an error string)
        if not any(final_response.startswith(p) for p in _ERROR_PREFIXES):
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": final_response})
        else:
            logger.debug("Skipping history append: response is an error string")

        # Store episode in the background (fire-and-forget) so the user gets their
        # response immediately and Graphiti's LLM extraction doesn't compete with
        # the next user turn for the rate-limit quota.
        if self.memory_available:
            asyncio.ensure_future(
                self._store_episode_background(user_message, final_response)
            )

        return final_response

    async def _store_episode_background(self, user_message: str, final_response: str) -> None:
        """Store a conversation episode with exponential-backoff retry on rate limit."""
        episode_body = f"User: {user_message}\nAgent: {final_response}"
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = 2 ** attempt  # 2 s, 4 s
                    logger.debug(f"Retrying episode storage in {delay}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                await self.memory_client.add_episode(
                    name=f"conversation_{datetime.now().isoformat()}",
                    episode_body=episode_body,
                    source="agent_conversation",
                    source_description=f"Conversation turn between user and {self.agent_config.name}",
                    reference_time=datetime.now(),
                    group_id=self.user_id,
                )
                logger.info("Conversation episode stored in knowledge graph")
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Episode storage attempt {attempt + 1}/{max_retries} failed: {e}", exc_info=True)
                else:
                    logger.error(f"Episode storage permanently failed after {max_retries} attempts: {e}", exc_info=True)

    def close(self) -> None:
        """Clean up resources"""
        # Note: Async memory client cleanup happens in SyncMemoryAgent.close()
        # Since this is an async agent, we can't call async methods here
        logger.debug("MemoryAgent resources cleaned up")


class SyncMemoryAgent:
    """Synchronous wrapper around MemoryAgent for CLI usage"""

    def __init__(self, user_id: Optional[str] = None):
        """Initialize the agent with shared event loop"""
        import asyncio

        try:
            # Create single event loop that will be shared with MemoryAgent
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            # Pass loop to async agent to avoid duplicate loop creation
            self._async_agent = MemoryAgent(user_id, loop=self._loop)
            logger.info(f"SyncMemoryAgent initialized for user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to initialize SyncMemoryAgent: {e}", exc_info=True)
            raise

    def process_message(self, user_message: str) -> str:
        """Process a user message synchronously"""
        return self._loop.run_until_complete(
            self._async_agent.process_message(user_message)
        )

    def clear_history(self) -> None:
        """Clear conversation history (properly encapsulated)"""
        self._async_agent.conversation_history = []

    def close(self) -> None:
        """Clean up resources"""
        try:
            # Close async memory client
            if self._async_agent.memory_client._graphiti:
                self._loop.run_until_complete(
                    self._async_agent.memory_client.close()
                )
                logger.debug("Memory client closed successfully")

            self._async_agent.close()
            logger.info("Agent resources closed successfully")
        except Exception as e:
            logger.warning(f"Error closing agent: {e}")
        finally:
            try:
                if self._loop and not self._loop.is_closed():
                    self._loop.close()
                    logger.debug("Event loop closed successfully")
            except Exception as e:
                logger.warning(f"Error closing event loop: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
