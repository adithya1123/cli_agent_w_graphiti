"""CLI interface for the Memory Agent with Graphiti and Azure OpenAI"""

import sys
import logging
from src.config import validate_all_configs
from src.agent import SyncMemoryAgent
from src.logging_config import setup_logging, get_logger

# Initialize logging
setup_logging(log_level="INFO")
logger = get_logger(__name__)


def print_welcome():
    """Print welcome message"""
    print("\n" + "=" * 60)
    print("Welcome to the Memory Agent")
    print("Azure OpenAI + Graphiti Temporal Knowledge Graph")
    print("=" * 60)
    print("\nAvailable commands:")
    print("  Type your message to chat with the agent")
    print("  'exit' or 'quit' to end the conversation")
    print("  'clear' to clear conversation history")
    print("  'help' for help")
    print("\n" + "-" * 60 + "\n")


def print_help():
    """Print help message"""
    print("\nCommands:")
    print("  exit, quit     - Exit the agent")
    print("  clear          - Clear conversation history")
    print("  help           - Show this help message")
    print("\nCapabilities:")
    print("  • Learns from conversation using temporal knowledge graph")
    print("  • Retrieves relevant memories from past conversations")
    print("  • Searches the web for current information when needed")
    print("  • Maintains context across multiple turns")
    print()


def main():
    """Main CLI interface for the agent"""
    try:
        # Validate configuration
        logger.info("Initializing agent...")
        validate_all_configs()

        # Initialize agent
        agent = SyncMemoryAgent(user_id="cli_user")
        logger.info("Agent initialized successfully!")

        print_welcome()

        # Main conversation loop
        while True:
            try:
                # Get user input
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                # Handle special commands
                if user_input.lower() in ["exit", "quit"]:
                    print("\nGoodbye!")
                    break

                if user_input.lower() == "clear":
                    agent.clear_history()
                    print("Conversation history cleared.\n")
                    continue

                if user_input.lower() == "help":
                    print_help()
                    continue

                # Process message
                print("\nAgent: ", end="", flush=True)
                response = agent.process_message(user_input)
                print(response)
                print()

            except KeyboardInterrupt:
                print("\n\nInterrupted by user. Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                print("Error: Could not process message. Please try again.\n")

        # Clean up
        agent.close()

    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
        print(f"Configuration Error: {e}")
        print("Please ensure all required environment variables are set in .env")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error initializing agent: {e}", exc_info=True)
        print(f"Error initializing agent: {e}")
        print("\nMake sure Neo4j is running. Start it with:")
        print("  docker-compose up -d")
        sys.exit(1)


if __name__ == "__main__":
    main()
