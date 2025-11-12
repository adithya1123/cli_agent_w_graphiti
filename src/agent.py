"""Main agent implementation with memory, web search, and Azure OpenAI function calling"""

import json
import logging
from datetime import datetime
from typing import Optional
from openai import AsyncAzureOpenAI, APIError, APIConnectionError

from src.config import AzureOpenAIConfig, AgentConfig
from src.graphiti_client import GraphitiMemory
from src.tools import ToolRegistry
from src.logging_config import get_logger

logger = get_logger(__name__)


class MemoryAgent:
    """Agent with temporal knowledge graph memory and web search capabilities"""

    def __init__(self, user_id: Optional[str] = None, loop=None):
        """Initialize the agent with optional event loop"""
        self.config = AzureOpenAIConfig()
        self.agent_config = AgentConfig()

        # Initialize Azure OpenAI client
        try:
            self.llm_client = AsyncAzureOpenAI(
                api_key=self.config.api_key,
                api_version=self.config.api_version,
                azure_endpoint=self.config.api_endpoint,
            )
            logger.info("Azure OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {e}", exc_info=True)
            raise RuntimeError(f"Cannot initialize LLM client: {str(e)}")

        # Initialize memory with optional external loop
        self.memory = GraphitiMemory(loop=loop)
        self.memory_available = False
        try:
            self.memory.initialize()
            self.memory_available = True
            logger.info("Memory system initialized successfully")
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
        """Get OpenAI function calling tool definitions"""
        return [
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
                # Build request kwargs
                kwargs = {
                    "model": self.config.chat_deployment_name,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1000,
                }

                # Add tools if provided
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"

                response = await self.llm_client.chat.completions.create(**kwargs)

                # Extract response content and tool calls
                message = response.choices[0].message
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
            return self.tools.call_tool("web_search", query=query)
        else:
            logger.warning(f"Unknown tool requested: {tool_name}")
            return f"Unknown tool: {tool_name}"

    async def _handle_tool_calls(self, tool_calls: list, messages: list) -> tuple[str, list]:
        """
        Handle tool calls from the LLM

        Returns:
            (final_response, updated_messages)
        """
        # Execute all tool calls
        for tool_call in tool_calls:
            tool_result = await self._execute_tool_call(tool_call)

            # Add tool result to messages
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": tool_call.function.name,
                    "content": tool_result,
                }
            )

        # Get final response from LLM with tool results
        try:
            response = await self.llm_client.chat.completions.create(
                model=self.config.chat_deployment_name,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
            )

            final_content = response.choices[0].message.content
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
                context = self.memory.get_context_for_query(
                    query=user_message,
                    group_id=self.user_id,
                    num_results=5,
                )
                logger.debug(f"Retrieved {len(context)} characters of context from memory")
            except Exception as e:
                logger.warning(f"Failed to retrieve context from memory: {e}")
                context = ""  # Continue without context

        # Get initial response with tools available
        # This will populate the messages list and handle any tool calls
        ai_result = await self._get_ai_response(user_message, context, tools=self._get_tool_definitions())

        # Process tool calls if the LLM decided to use them
        final_response = ai_result["content"]
        if ai_result["tool_calls"]:
            # Build messages for tool handling
            system_message = self._create_system_prompt()
            if context:
                system_message += f"\n\nContext from your memories:\n{context}"

            messages = [
                {"role": "system", "content": system_message},
            ]

            # Add conversation history
            history_limit = self.agent_config.conversation_history_limit
            for msg in self.conversation_history[-history_limit:]:
                messages.append(msg)

            # Add current user message
            messages.append({"role": "user", "content": user_message})

            # Add the assistant response with tool calls
            messages.append({
                "role": "assistant",
                "content": ai_result["content"],
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

        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": final_response})

        # Store in knowledge graph as a new episode with user isolation (non-critical)
        if self.memory_available:
            try:
                episode_body = f"User: {user_message}\nAgent: {final_response}"
                self.memory.add_episode(
                    name=f"conversation_{datetime.now().isoformat()}",
                    episode_body=episode_body,
                    source="agent_conversation",
                    source_description=f"Conversation turn between user and {self.agent_config.name}",
                    reference_time=datetime.now(),
                    group_id=self.user_id,  # User isolation via group_id
                )
                logger.debug("Conversation episode stored in knowledge graph")
            except Exception as e:
                logger.warning(f"Could not store episode in knowledge graph (memory system may be unavailable): {e}")
        else:
            logger.debug("Memory system unavailable; conversation episode not stored")

        return final_response

    def close(self) -> None:
        """Clean up resources"""
        try:
            if self.memory_available:
                self.memory.close()
                logger.info("Memory system closed successfully")
        except Exception as e:
            logger.warning(f"Error closing memory system: {e}")


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
