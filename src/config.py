"""Configuration management for agent environment variables"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class AzureOpenAIConfig:
    """Azure OpenAI Configuration"""
    api_key: str = os.getenv("AZURE_OPENAI_API_KEY")
    api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
    api_endpoint: str = os.getenv("AZURE_OPENAI_API_ENDPOINT")
    chat_deployment_name: str = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-4o")
    embedding_deployment_name: str = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "embedding-3-small")

    @classmethod
    def validate(cls) -> None:
        """Validate required Azure OpenAI configuration"""
        if not cls.api_key:
            raise ValueError("AZURE_OPENAI_API_KEY not set in environment")
        if not cls.api_endpoint:
            raise ValueError("AZURE_OPENAI_API_ENDPOINT not set in environment")


class Neo4jConfig:
    """Neo4j Database Configuration"""
    uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user: str = os.getenv("NEO4J_USER", "neo4j")
    password: str = os.getenv("NEO4J_PASSWORD", "password")

    @classmethod
    def validate(cls) -> None:
        """Validate required Neo4j configuration"""
        if not cls.uri:
            raise ValueError("NEO4J_URI not set in environment")


class TavilyConfig:
    """Tavily Search Configuration"""
    api_key: str = os.getenv("TAVILY_API_KEY")

    @classmethod
    def validate(cls) -> None:
        """Validate required Tavily configuration"""
        if not cls.api_key:
            raise ValueError("TAVILY_API_KEY not set in environment")


class AgentConfig:
    """Agent Configuration"""
    name: str = os.getenv("AGENT_NAME", "Knowledge Graph Agent")
    conversation_history_limit: int = int(os.getenv("CONVERSATION_HISTORY_LIMIT", "10"))


def validate_all_configs() -> None:
    """Validate all required configurations"""
    AzureOpenAIConfig.validate()
    Neo4jConfig.validate()
    TavilyConfig.validate()
