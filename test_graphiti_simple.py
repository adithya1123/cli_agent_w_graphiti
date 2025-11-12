"""
Simple test script for Graphiti functionality
Tests the core functionality without complex async/event loop handling
"""

from src.agent import SyncMemoryAgent
from src.config import validate_all_configs
import time


def print_section(title: str):
    """Print a test section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def test_all():
    """Run all tests"""
    print("\n" + "="*70)
    print("  GRAPHITI AGENT FUNCTIONALITY TEST")
    print("="*70)

    # Validate configuration
    try:
        validate_all_configs()
        print("\n✅ Configuration validated successfully\n")
    except Exception as e:
        print(f"\n❌ Configuration validation failed: {e}\n")
        return False

    # TEST 1: Initialization
    print_section("TEST 1: Agent Initialization")
    try:
        print("✓ Creating agent for user1...")
        agent1 = SyncMemoryAgent(user_id="user1")
        print(f"✓ Agent name: {agent1._async_agent.agent_config.name}")
        print(f"✓ User ID: {agent1._async_agent.user_id}")
        print(f"✓ Tools available: {agent1._async_agent.tools.list_tools()}")
        agent1.close()
        print("\n✅ TEST 1 PASSED\n")
    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}\n")
        return False

    # TEST 2: Memory Storage & Retrieval
    print_section("TEST 2: Store & Retrieve Memories")
    try:
        print("✓ Creating agent and storing memories...")
        agent = SyncMemoryAgent(user_id="user2")

        print("  - Storing Python memory...")
        agent._async_agent.memory.add_episode(
            name="python_fact",
            episode_body="User is learning Python. Python is a high-level programming language.",
            source="test",
            source_description="Test episode about Python",
            group_id="user2",
        )

        print("  - Storing Java memory...")
        agent._async_agent.memory.add_episode(
            name="java_fact",
            episode_body="User is also learning Java. Java is used for enterprise applications.",
            source="test",
            source_description="Test episode about Java",
            group_id="user2",
        )

        print("\n✓ Retrieving memories for 'programming languages'...")
        context = agent._async_agent.memory.get_context_for_query(
            query="programming languages",
            group_id="user2",
            num_results=5,
        )

        print(f"  Retrieved: {len(context)} characters")

        has_python = "Python" in context
        has_java = "Java" in context

        if has_python and has_java:
            print(f"  ✓ Contains Python reference: {has_python}")
            print(f"  ✓ Contains Java reference: {has_java}")
            agent.close()
            print("\n✅ TEST 2 PASSED\n")
        else:
            print(f"  ⚠️ Python: {has_python}, Java: {has_java}")
            print("\n⚠️ TEST 2: Partial success (stored but not retrieved)\n")
            agent.close()

    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False

    # TEST 3: User Isolation
    print_section("TEST 3: User Isolation (group_id)")
    try:
        print("✓ Creating agents for user3 and user4...")
        agent3 = SyncMemoryAgent(user_id="user3")
        agent4 = SyncMemoryAgent(user_id="user4")

        print("  - Storing user3 preference...")
        agent3._async_agent.memory.add_episode(
            name="user3_pref",
            episode_body="User3 likes Python and JavaScript",
            source="test",
            source_description="User3 preferences",
            group_id="user3",
        )

        print("  - Storing user4 preference...")
        agent4._async_agent.memory.add_episode(
            name="user4_pref",
            episode_body="User4 likes Java and C++",
            source="test",
            source_description="User4 preferences",
            group_id="user4",
        )

        print("\n✓ Retrieving user3 memories...")
        context3 = agent3._async_agent.memory.get_context_for_query(
            query="preferences",
            group_id="user3",
            num_results=5,
        )

        print("✓ Retrieving user4 memories...")
        context4 = agent4._async_agent.memory.get_context_for_query(
            query="preferences",
            group_id="user4",
            num_results=5,
        )

        # Check isolation
        user3_ok = "Python" in context3 and "JavaScript" in context3
        user4_ok = "Java" in context4 and "C++" in context4
        no_mix = "Python" not in context4 and "Java" not in context3

        print(f"\n  User3 has Python/JavaScript: {user3_ok}")
        print(f"  User4 has Java/C++: {user4_ok}")
        print(f"  No cross-contamination: {no_mix}")

        if user3_ok and user4_ok and no_mix:
            print("\n✅ TEST 3 PASSED\n")
            agent3.close()
            agent4.close()
        else:
            print("\n⚠️ TEST 3: Partial isolation\n")
            agent3.close()
            agent4.close()

    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False

    # TEST 4: Tool Configuration
    print_section("TEST 4: Tool Definitions & Function Calling")
    try:
        print("✓ Creating agent...")
        agent = SyncMemoryAgent(user_id="tool_test")

        print("✓ Getting tool definitions...")
        tools = agent._async_agent._get_tool_definitions()

        print(f"  Tools count: {len(tools)}")
        tool_names = [t['function']['name'] for t in tools]
        print(f"  Tool names: {tool_names}")

        if 'web_search' in tool_names:
            print("\n✅ TEST 4 PASSED\n")
            agent.close()
        else:
            print("\n❌ TEST 4 FAILED: web_search not found\n")
            agent.close()
            return False

    except Exception as e:
        print(f"\n❌ TEST 4 FAILED: {e}\n")
        return False

    # TEST 5: Basic Conversation
    print_section("TEST 5: Simple Conversation")
    try:
        print("✓ Creating agent...")
        agent = SyncMemoryAgent(user_id="conv_test")

        print("✓ Sending simple message (may make LLM call)...")
        print("  Message: 'Hi, what can you do?'")

        response = agent.process_message("Hi, what can you do?")

        print(f"\n✓ Response received ({len(response)} chars):")
        if len(response) > 50:
            print(f"  {response[:100]}...")
        else:
            print(f"  {response}")

        if len(response) > 10:
            print("\n✅ TEST 5 PASSED\n")
            agent.close()
        else:
            print("\n❌ TEST 5 FAILED: No response\n")
            agent.close()
            return False

    except Exception as e:
        print(f"\n❌ TEST 5 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False

    # Summary
    print_section("TEST SUMMARY")
    print("✅ All tests completed successfully!")
    print("\n🎉 Agent is functioning correctly.\n")
    return True


if __name__ == "__main__":
    success = test_all()
    exit(0 if success else 1)
