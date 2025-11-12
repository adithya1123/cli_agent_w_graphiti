"""CLI interface for the Memory Agent with Graphiti and OpenAI"""

import sys
import logging
from src.config import validate_all_configs
from src.agent import SyncMemoryAgent
from src.user_session import UserSessionManager
from src.logging_config import setup_logging, get_logger

# Initialize logging
setup_logging(log_level="INFO")
logger = get_logger(__name__)


def print_welcome(user_id: str):
    """Print welcome message with current user"""
    print("\n" + "=" * 70)
    print("Welcome to the Memory Agent")
    print("OpenAI + Graphiti Temporal Knowledge Graph")
    print("=" * 70)
    print(f"\n👤 Current User: {user_id}")
    print("\nAvailable commands:")
    print("  Type your message to chat with the agent")
    print("  'help'          - Show help message")
    print("  'whoami'        - Show current user")
    print("  'switch'        - Switch to different user")
    print("  'clear'         - Clear conversation history")
    print("  'exit' or 'quit' - End the conversation")
    print("\n" + "-" * 70 + "\n")


def print_help():
    """Print help message"""
    print("\nCommands:")
    print("  whoami         - Show current user")
    print("  switch         - Switch to different user")
    print("  clear          - Clear conversation history for current user")
    print("  help           - Show this help message")
    print("  exit, quit     - Exit the agent")
    print("\nCapabilities:")
    print("  • Multi-user support with separate memory per user")
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

        # Get user ID with optional persistence
        user_id = UserSessionManager.prompt_for_user()
        logger.info(f"User session started: {user_id}")

        # Initialize agent with user_id
        agent = SyncMemoryAgent(user_id=user_id)
        logger.info(f"Agent initialized for user: {user_id}")

        print_welcome(user_id)

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

                if user_input.lower() == "whoami":
                    print(f"👤 Current user: {user_id}\n")
                    continue

                if user_input.lower() == "switch":
                    print("\nSwitching user...")
                    agent.close()
                    user_id = UserSessionManager.prompt_for_user()
                    agent = SyncMemoryAgent(user_id=user_id)
                    logger.info(f"User switched to: {user_id}")
                    print(f"✓ Switched to user: {user_id}\n")
                    continue

                if user_input.lower() == "clear":
                    agent.clear_history()
                    print("✓ Conversation history cleared.\n")
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
