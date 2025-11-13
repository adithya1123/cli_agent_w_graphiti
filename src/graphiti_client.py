"""Graphiti client wrapper for temporal knowledge graph memory with OpenAI"""

import logging
from datetime import datetime
from typing import Optional, Any
import asyncio
from enum import Enum

from openai import AsyncOpenAI
from graphiti_core import Graphiti
from graphiti_core.llm_client import LLMConfig, OpenAIClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient

from src.config import OpenAIConfig, Neo4jConfig
from src.logging_config import get_logger

logger = get_logger(__name__)


# Graphiti EpisodeType enum
class EpisodeType(str, Enum):
    """Episode source types for Graphiti"""
    text = "text"
    json = "json"
    md = "md"


class GraphitiMemoryClient:
    """Wrapper around Graphiti for managing temporal knowledge graph memory"""

    def __init__(self):
        """Initialize Graphiti client with OpenAI"""
        self.config = OpenAIConfig()
        self.neo4j_config = Neo4jConfig()
        self._graphiti: Optional[Graphiti] = None
        self._llm_client: Optional[OpenAIClient] = None

    async def initialize(self) -> None:
        """Initialize Graphiti and OpenAI clients"""
        # Build client kwargs for LLM - include base_url if using Azure endpoint
        llm_client_kwargs = {"api_key": self.config.api_key}
        if self.config.api_endpoint:
            llm_client_kwargs["base_url"] = self.config.api_endpoint

        # Build client kwargs for embeddings - support separate resource
        embedder_client_kwargs = {
            "api_key": self.config.embedding_api_key or self.config.api_key
        }
        if self.config.embedding_endpoint:
            embedder_client_kwargs["base_url"] = self.config.embedding_endpoint

        # Create OpenAI async client for LLM
        llm_client = AsyncOpenAI(**llm_client_kwargs)

        # Create OpenAI async client for embeddings (may use different resource)
        embedder_client = AsyncOpenAI(**embedder_client_kwargs)

        # Initialize LLM client for Graphiti with OpenAI model IDs
        # LLMConfig is required to properly configure OpenAI for Structured Outputs
        llm_config = LLMConfig(
            model=self.config.chat_model,
            small_model=self.config.chat_model,
        )
        self._llm_client = OpenAIClient(
            config=llm_config,
            client=llm_client
        )

        # Initialize embedder for Graphiti
        embedder = OpenAIEmbedder(
            client=embedder_client,
            config=OpenAIEmbedderConfig(
                embedding_model=self.config.embedding_model,
            ),
        )

        # Initialize cross_encoder (reranker) for OpenAI
        cross_encoder = OpenAIRerankerClient(
            config=llm_config,
            client=llm_client
        )

        # Initialize Graphiti with OpenAI for all components
        self._graphiti = Graphiti(
            uri=self.neo4j_config.uri,
            user=self.neo4j_config.user,
            password=self.neo4j_config.password,
            llm_client=self._llm_client,
            embedder=embedder,
            cross_encoder=cross_encoder,
        )

    async def add_episode(
        self,
        name: str,
        episode_body: str,
        source: str = "text",
        source_description: Optional[str] = None,
        reference_time: Optional[datetime] = None,
        group_id: Optional[str] = None,
    ) -> None:
        """Add an episode (conversation turn) to the knowledge graph with user isolation"""
        if not self._graphiti:
            raise RuntimeError("Graphiti not initialized. Call initialize() first.")

        if reference_time is None:
            reference_time = datetime.now()

        if source_description is None:
            source_description = f"Episode from {source}"

        try:
            # Convert source string to EpisodeType enum
            # Valid values: "text", "json", "md" (markdown)
            source_enum = EpisodeType.text  # Default to text for conversation episodes
            if source.lower() == "json":
                source_enum = EpisodeType.json
            elif source.lower() == "md" or source.lower() == "markdown":
                source_enum = EpisodeType.md

            # Build kwargs for add_episode - include group_id for user isolation
            kwargs = {
                "name": name,
                "episode_body": episode_body,
                "source": source_enum,  # Use enum instead of string
                "source_description": source_description,
                "reference_time": reference_time,
            }
            if group_id:
                kwargs["group_id"] = group_id

            await self._graphiti.add_episode(**kwargs)
        except Exception as e:
            logger.error(f"Error adding episode: {e}", exc_info=True)
            raise

    async def search(
        self,
        query: str,
        num_results: int = 5,
        user_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Search the knowledge graph for relevant information"""
        if not self._graphiti:
            raise RuntimeError("Graphiti not initialized. Call initialize() first.")

        try:
            # Use group_ids parameter (plural - Graphiti uses group_ids for user isolation)
            results = await self._graphiti.search(
                query=query,
                num_results=num_results,
                group_ids=[user_id] if user_id else None,  # Graphiti expects a list
            )
            return results
        except Exception as e:
            logger.error(f"Error searching knowledge graph: {e}", exc_info=True)
            raise

    async def get_context_for_query(
        self,
        query: str,
        user_id: Optional[str] = None,
        num_results: int = 5,
    ) -> str:
        """Get formatted context string from knowledge graph for a query"""
        try:
            search_results = await self.search(
                query=query,
                num_results=num_results,
                user_id=user_id,
            )

            # search_results is a list from Graphiti
            if not search_results:
                return "No relevant memories found."

            # Format search results into a context string
            context_parts = ["Relevant memories:"]
            for result in search_results:
                if isinstance(result, dict):
                    # Extract text from result - could be in different formats
                    text = result.get('content') or result.get('text') or result.get('name') or str(result)
                    context_parts.append(f"- {text}")
                else:
                    context_parts.append(f"- {result}")

            return "\n".join(context_parts)

        except Exception as e:
            logger.error(f"Error getting context: {e}", exc_info=True)
            return "Error retrieving memories."

    async def close(self) -> None:
        """Close Graphiti and clean up resources"""
        if self._graphiti:
            # Graphiti uses async context managers, but we'll try to close if available
            try:
                if hasattr(self._graphiti, "close"):
                    await self._graphiti.close()
            except Exception as e:
                logger.warning(f"Error closing Graphiti: {e}")

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


# Synchronous wrapper for convenience
class GraphitiMemory:
    """Synchronous wrapper around GraphitiMemoryClient with external event loop management"""

    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        """Initialize the wrapper with optional event loop"""
        self._client = GraphitiMemoryClient()
        self._loop = loop
        self._owns_loop = False

    def initialize(self) -> None:
        """Initialize the Graphiti client"""
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._owns_loop = True

        self._loop.run_until_complete(self._client.initialize())

    def add_episode(
        self,
        name: str,
        episode_body: str,
        source: str = "agent",
        source_description: Optional[str] = None,
        reference_time: Optional[datetime] = None,
        group_id: Optional[str] = None,
    ) -> None:
        """Add an episode to the knowledge graph with user isolation via group_id"""
        if not self._loop:
            raise RuntimeError("Not initialized. Call initialize() first.")

        try:
            # Try to run the coroutine normally
            self._loop.run_until_complete(
                self._client.add_episode(
                    name, episode_body, source, source_description, reference_time, group_id
                )
            )
        except RuntimeError as e:
            # If loop is already running (called from async context), use ensure_future
            if "This event loop is already running" in str(e):
                import asyncio
                # Schedule the task but don't wait for it (fire and forget)
                # This prevents blocking the running event loop
                asyncio.ensure_future(
                    self._client.add_episode(
                        name, episode_body, source, source_description, reference_time, group_id
                    ),
                    loop=self._loop
                )
                logger.debug("Episode storage scheduled (non-blocking in running event loop)")
            else:
                raise

    def search(
        self,
        query: str,
        num_results: int = 5,
        user_id: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Search the knowledge graph"""
        if not self._loop:
            raise RuntimeError("Not initialized. Call initialize() first.")

        try:
            # Use group_id for user isolation if provided
            return self._loop.run_until_complete(
                self._client.search(query, num_results, group_id or user_id)
            )
        except RuntimeError as e:
            if "This event loop is already running" in str(e):
                # Can't block in running event loop - return empty result
                logger.warning("Memory search failed: cannot run in already-running event loop")
                return {"results": []}
            raise

    def get_context_for_query(
        self,
        query: str,
        user_id: Optional[str] = None,
        num_results: int = 5,
        group_id: Optional[str] = None,
    ) -> str:
        """Get context string from the knowledge graph with user isolation"""
        if not self._loop:
            raise RuntimeError("Not initialized. Call initialize() first.")

        try:
            # Use group_id for user isolation if provided
            return self._loop.run_until_complete(
                self._client.get_context_for_query(query, group_id or user_id, num_results)
            )
        except RuntimeError as e:
            if "This event loop is already running" in str(e):
                # Can't block in running event loop - return empty context
                logger.warning("Memory context retrieval failed: cannot run in already-running event loop")
                return ""
            raise

    def close(self) -> None:
        """Close the client and clean up"""
        if self._loop:
            self._loop.run_until_complete(self._client.close())
            if self._owns_loop:
                self._loop.close()

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
