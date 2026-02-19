"""Tools for the agent, including web search"""

import logging
from typing import Optional
from tavily import TavilyClient

from src.config import TavilyConfig
from src.logging_config import get_logger

logger = get_logger(__name__)


class WebSearchTool:
    """Web search tool using Tavily API"""

    def __init__(self):
        """Initialize Tavily client"""
        try:
            self.config = TavilyConfig()
            self.client = TavilyClient(api_key=self.config.api_key)
            logger.info("Tavily web search client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Tavily client: {e}", exc_info=True)
            self.client = None

    def search(
        self,
        query: str,
        max_results: int = 5,
        include_answer: bool = True,
    ) -> dict:
        """
        Search the web using Tavily

        Args:
            query: Search query
            max_results: Maximum number of results to return
            include_answer: Whether to include AI-generated answer

        Returns:
            Dictionary with search results
        """
        if not self.client:
            logger.warning("Tavily client not initialized")
            return {"error": "Search service not available", "results": []}

        max_retries = 2
        for attempt in range(max_retries):
            try:
                logger.info(f"Executing web search for: {query}")
                response = self.client.search(
                    query=query,
                    max_results=max_results,
                    include_answer=include_answer,
                )
                logger.debug(f"Web search returned {len(response.get('results', []))} results")
                return response
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Web search failed after {max_retries} attempts: {e}", exc_info=True)
                    return {"error": f"Search failed: {str(e)}", "results": []}
                logger.warning(f"Web search attempt {attempt + 1} failed: {e}")

        return {"error": "Search service unavailable", "results": []}

    def format_search_results(self, response: dict) -> str:
        """Format search results into a readable string"""
        if "error" in response:
            return f"Search error: {response['error']}"

        formatted_parts = []

        # Add AI-generated answer if available
        if response.get("answer"):
            formatted_parts.append(f"Answer: {response['answer']}\n")

        # Add search results (content capped to 300 chars each to limit token usage)
        if response.get("results"):
            formatted_parts.append("Sources:")
            for idx, result in enumerate(response["results"], 1):
                title = result.get("title", "")
                url = result.get("url", "")
                content = result.get("content", "")
                if len(content) > 300:
                    content = content[:300] + "..."
                formatted_parts.append(f"{idx}. {title}\n   URL: {url}\n   {content}\n")

        return "\n".join(formatted_parts) if formatted_parts else "No results found"

    def search_and_format(
        self,
        query: str,
        max_results: int = 5,
    ) -> str:
        """Search the web and return formatted results"""
        response = self.search(query, max_results=max_results)
        return self.format_search_results(response)


class ToolRegistry:
    """Registry of available tools for the agent"""

    def __init__(self):
        """Initialize tool registry with available tools"""
        try:
            self.web_search = WebSearchTool()
            self.tools = {
                "web_search": self.web_search.search_and_format,
            }
            logger.info(f"Tool registry initialized with tools: {list(self.tools.keys())}")
        except Exception as e:
            logger.error(f"Failed to initialize tool registry: {e}", exc_info=True)
            self.tools = {}

    def get_tool(self, tool_name: str):
        """Get a tool by name"""
        if tool_name not in self.tools:
            logger.warning(f"Tool '{tool_name}' not found in registry")
        return self.tools.get(tool_name)

    def call_tool(self, tool_name: str, **kwargs) -> str:
        """Call a tool by name with arguments"""
        logger.debug(f"Calling tool: {tool_name} with kwargs: {list(kwargs.keys())}")
        tool = self.get_tool(tool_name)
        if not tool:
            error_msg = f"Tool '{tool_name}' not found"
            logger.error(error_msg)
            return error_msg

        try:
            result = tool(**kwargs)
            logger.debug(f"Tool '{tool_name}' executed successfully")
            return result
        except Exception as e:
            logger.error(f"Error calling tool '{tool_name}': {e}", exc_info=True)
            return f"Error calling tool '{tool_name}': {str(e)}"

    def list_tools(self) -> list[str]:
        """List available tools"""
        return list(self.tools.keys())
