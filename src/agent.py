"""Main agent implementation with memory, web search, and Azure OpenAI function calling"""

import json
from datetime import datetime
from typing import Optional
from openai import AsyncAzureOpenAI

from src.config import AzureOpenAIConfig, AgentConfig
from src.graphiti_client import GraphitiMemory
from src.tools import ToolRegistry


class MemoryAgent:
    """Agent with temporal knowledge graph memory and web search capabilities"""

    def __init__(self, user_id: Optional[str] = None, loop=None):
        """Initialize the agent with optional event loop"""
        self.config = AzureOpenAIConfig()
        self.agent_config = AgentConfig()

        # Initialize Azure OpenAI client
        self.llm_client = AsyncAzureOpenAI(
            api_key=self.config.api_key,
            api_version=self.config.api_version,
            azure_endpoint=self.config.api_endpoint,
        )

        # Initialize memory with optional external loop
        self.memory = GraphitiMemory(loop=loop)
        self.memory.initialize()

        # Initialize tools
        self.tools = ToolRegistry()

        # User ID for tracking conversations
        self.user_id = user_id or "default_user"

        # Conversation history for context window
        self.conversation_history: list[dict] = []

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
        except Exception as e:
            print(f"Error getting AI response: {e}")
            return {"content": f"Error generating response: {str(e)}", "tool_calls": None}

    async def _execute_tool_call(self, tool_call) -> str:
        """Execute a single tool call and return the result"""
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)

        if tool_name == "web_search":
            query = tool_args.get("query", "")
            print(f"  [Searching web for: {query}]")
            return self.tools.call_tool("web_search", query=query)
        else:
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
            print(f"Error getting final response after tool calls: {e}")
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
        context = self.memory.get_context_for_query(
            query=user_message,
            group_id=self.user_id,
            num_results=5,
        )

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

        # Store in knowledge graph as a new episode with user isolation
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
        except Exception as e:
            print(f"Warning: Could not store episode in knowledge graph: {e}")

        return final_response

    def close(self) -> None:
        """Clean up resources"""
        self.memory.close()


class SyncMemoryAgent:
    """Synchronous wrapper around MemoryAgent for CLI usage"""

    def __init__(self, user_id: Optional[str] = None):
        """Initialize the agent with shared event loop"""
        import asyncio

        # Create single event loop that will be shared with MemoryAgent
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        # Pass loop to async agent to avoid duplicate loop creation
        self._async_agent = MemoryAgent(user_id, loop=self._loop)

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
        self._async_agent.close()
        self._loop.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
