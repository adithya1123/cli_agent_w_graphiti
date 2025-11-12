"""Tools for the agent, including web search"""

from typing import Optional
from tavily import TavilyClient

from src.config import TavilyConfig


class WebSearchTool:
    """Web search tool using Tavily API"""

    def __init__(self):
        """Initialize Tavily client"""
        self.config = TavilyConfig()
        self.client = TavilyClient(api_key=self.config.api_key)

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
        try:
            response = self.client.search(
                query=query,
                max_results=max_results,
                include_answer=include_answer,
            )
            return response
        except Exception as e:
            print(f"Error during web search: {e}")
            return {"error": str(e), "results": []}

    def format_search_results(self, response: dict) -> str:
        """Format search results into a readable string"""
        if "error" in response:
            return f"Search error: {response['error']}"

        formatted_parts = []

        # Add AI-generated answer if available
        if response.get("answer"):
            formatted_parts.append(f"Answer: {response['answer']}\n")

        # Add search results
        if response.get("results"):
            formatted_parts.append("Sources:")
            for idx, result in enumerate(response["results"], 1):
                title = result.get("title", "")
                url = result.get("url", "")
                content = result.get("content", "")
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
        self.web_search = WebSearchTool()
        self.tools = {
            "web_search": self.web_search.search_and_format,
        }

    def get_tool(self, tool_name: str):
        """Get a tool by name"""
        return self.tools.get(tool_name)

    def call_tool(self, tool_name: str, **kwargs) -> str:
        """Call a tool by name with arguments"""
        tool = self.get_tool(tool_name)
        if not tool:
            return f"Tool '{tool_name}' not found"

        try:
            return tool(**kwargs)
        except Exception as e:
            return f"Error calling tool '{tool_name}': {str(e)}"

    def list_tools(self) -> list[str]:
        """List available tools"""
        return list(self.tools.keys())
