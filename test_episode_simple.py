#!/usr/bin/env python3
"""Simple test for episode creation with Graphiti Azure OpenAI"""

import asyncio
from datetime import datetime
from src.graphiti_client import GraphitiMemoryClient

async def test_episode_creation():
    """Test adding an episode"""
    client = GraphitiMemoryClient()

    try:
        print("1. Initializing Graphiti...")
        await client.initialize()
        print("   ✅ Initialized")

        print("\n2. Creating a test episode...")
        episode_body = """User: What is Python?
Agent: Python is a high-level programming language."""

        await client.add_episode(
            name=f"test_episode_{datetime.now().isoformat()}",
            episode_body=episode_body,
            source="text",
            source_description="Test episode",
            group_id="test_user"
        )
        print("   ✅ Episode created and stored")

        print("\n3. Searching for the episode...")
        results = await client.search(
            query="Python programming",
            num_results=5,
            user_id="test_user"
        )
        # results is now a list from Graphiti
        print(f"   ✅ Search returned {len(results)} results")
        if results:
            print(f"   First result: {results[0]}")

        print("\n" + "="*50)
        print("✅ ALL TESTS PASSED!")
        print("="*50)
        print("\nGraphiti with OpenAI client is working correctly!")

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_episode_creation())
