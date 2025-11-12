"""Main agent implementation with memory, web search, and Azure OpenAI"""

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

    def _create_system_prompt(self) -> str:
        """Create the system prompt for the agent"""
        return f"""You are {self.agent_config.name}, a helpful AI assistant with access to a temporal knowledge graph memory system and the ability to search the web for current information.

Your capabilities:
1. You have access to a temporal knowledge graph that stores facts learned from past conversations
2. You can search the web for current information using the web_search tool
3. You maintain a coherent conversation with the user
4. You learn and remember facts about the user and the world from your conversations

When responding:
- Use relevant memories from past conversations when available
- Search the web when you need current information or when your knowledge is insufficient
- Be clear about when you're using past memories vs. current information from the web
- Be conversational and helpful
- Update your knowledge with new information from each conversation

Available tools:
- web_search(query): Search the web for information"""

    async def _get_ai_response(self, user_message: str, context: str = "") -> str:
        """Get response from Azure OpenAI with context from memory"""
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
            response = await self.llm_client.chat.completions.create(
                model=self.config.chat_deployment_name,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
            )

            return response.choices[0].message.content
        except Exception as e:
            print(f"Error getting AI response: {e}")
            return f"Error generating response: {str(e)}"

    async def _handle_web_search(self, query: str) -> str:
        """Handle web search request"""
        print(f"  [Searching web for: {query}]")
        result = self.tools.call_tool("web_search", query=query)
        return result

    def _should_use_web_search(self, user_message: str) -> bool:
        """Determine if web search should be used"""
        # Simple heuristic: use web search for questions about current events,
        # recent information, or when explicitly asked
        keywords = [
            "today",
            "current",
            "latest",
            "recent",
            "now",
            "2024",
            "2025",
            "how much",
            "what is the price",
            "news",
            "search",
        ]
        return any(keyword in user_message.lower() for keyword in keywords)

    async def process_message(self, user_message: str) -> str:
        """
        Process a user message and generate a response

        Args:
            user_message: The user's input message

        Returns:
            The agent's response
        """
        # Search memory for relevant context
        context = self.memory.get_context_for_query(
            query=user_message,
            user_id=self.user_id,
            num_results=5,
        )

        # Optionally search the web
        web_context = ""
        if self._should_use_web_search(user_message):
            web_context = await self._handle_web_search(user_message)

        # Combine contexts
        full_context = context
        if web_context:
            full_context += f"\n\nWeb search results:\n{web_context}"

        # Get AI response
        response = await self._get_ai_response(user_message, full_context)

        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": response})

        # Store in knowledge graph as a new episode with user isolation
        try:
            episode_body = f"User: {user_message}\nAgent: {response}"
            self.memory.add_episode(
                name=f"conversation_{datetime.now().isoformat()}",
                episode_body=episode_body,
                source="agent_conversation",
                reference_time=datetime.now(),
                group_id=self.user_id,  # User isolation via group_id
            )
        except Exception as e:
            print(f"Warning: Could not store episode in knowledge graph: {e}")

        return response

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
