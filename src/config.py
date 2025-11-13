"""Configuration management for agent environment variables"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class OpenAIConfig:
    """OpenAI Configuration - supports both openai.com and Azure OpenAI with v1 API"""
    api_key: str = os.getenv("OPENAI_API_KEY")
    api_endpoint: str = os.getenv("OPENAI_API_ENDPOINT", "")  # Azure endpoint for chat, empty for openai.com
    chat_model: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o")

    # Embedding configuration (can be different resource in Azure)
    embedding_api_key: str = os.getenv("OPENAI_EMBEDDING_API_KEY", "")  # Leave empty to use main api_key
    embedding_endpoint: str = os.getenv("OPENAI_EMBEDDING_ENDPOINT", "")  # Separate endpoint for embeddings
    embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    @classmethod
    def validate(cls) -> None:
        """Validate required OpenAI configuration"""
        if not cls.api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")


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
    OpenAIConfig.validate()
    Neo4jConfig.validate()
    TavilyConfig.validate()
