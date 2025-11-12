#!/usr/bin/env python
"""Quick demo to test the agent - runs a sample conversation"""

import sys
from src.agent import SyncMemoryAgent
from src.logging_config import setup_logging

# Setup logging to see what's happening
setup_logging(log_level="INFO")

def main():
    print("\n" + "="*70)
    print("  AGENT DEMO - Interactive Test")
    print("="*70 + "\n")

    try:
        # Initialize agent
        print("📦 Initializing agent...")
        agent = SyncMemoryAgent(user_id="demo_user")
        print("✅ Agent initialized!\n")

        # Test conversations
        test_messages = [
            "Hi, what can you do?",
            "Can you search the web for information about Claude AI?",
            "What did you just find?",
        ]

        print("🚀 Starting demo conversation...\n")

        for message in test_messages:
            print(f"📝 You: {message}")
            print("-" * 70)

            response = agent.process_message(message)

            print(f"🤖 Agent:")
            print(response)
            print("\n")

        # Cleanup
        agent.close()
        print("✅ Demo complete! Agent closed successfully.")

    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
