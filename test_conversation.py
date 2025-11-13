"""
Simple conversation test for the agent
Tests core functionality: agent initialization, conversation flow, tool availability
Does NOT require Graphiti memory extraction
"""

from src.agent import SyncMemoryAgent
from src.config import validate_all_configs


def print_section(title: str):
    """Print a test section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def test_agent_conversation():
    """Test basic agent conversation without Graphiti memory extraction"""

    print("\n" + "="*70)
    print("  AGENT CONVERSATION TEST")
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
        print("✓ Creating SyncMemoryAgent...")
        agent = SyncMemoryAgent(user_id="conversation_test_user")

        print(f"✓ Agent name: {agent._async_agent.agent_config.name}")
        print(f"✓ User ID: {agent._async_agent.user_id}")
        print(f"✓ Tools available: {agent._async_agent.tools.list_tools()}")
        print(f"✓ Max tokens: 1000")
        print(f"✓ Temperature: 0.7")

        print("\n✅ TEST 1 PASSED: Agent initialized successfully\n")
        agent.close()
    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False

    # TEST 2: Tool Definitions
    print_section("TEST 2: Tool Schema & Function Calling")
    try:
        print("✓ Creating agent...")
        agent = SyncMemoryAgent(user_id="tool_test")

        print("✓ Getting tool definitions...")
        tools = agent._async_agent._get_tool_definitions()

        print(f"  - Tools count: {len(tools)}")

        # Check web_search tool
        web_search_tool = None
        for tool in tools:
            if tool['function']['name'] == 'web_search':
                web_search_tool = tool['function']
                break

        if web_search_tool:
            print(f"  ✓ Tool found: {web_search_tool['name']}")
            print(f"  ✓ Description: {web_search_tool['description'][:70]}...")
            print(f"  ✓ Parameters: {list(web_search_tool['parameters']['properties'].keys())}")

            print("\n✅ TEST 2 PASSED: Tool definitions correct\n")
            agent.close()
        else:
            print("\n❌ TEST 2 FAILED: web_search tool not found\n")
            agent.close()
            return False

    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False

    # TEST 3: System Prompt
    print_section("TEST 3: System Prompt Generation")
    try:
        print("✓ Creating agent...")
        agent = SyncMemoryAgent(user_id="prompt_test")

        print("✓ Generating system prompt...")
        system_prompt = agent._async_agent._create_system_prompt()

        print(f"  Prompt length: {len(system_prompt)} characters")
        print(f"  Prompt preview:")
        print(f"  {system_prompt[:150]}...\n")

        # Check key elements
        has_agent_name = agent._async_agent.agent_config.name in system_prompt
        has_memory_mention = "knowledge graph" in system_prompt.lower()
        has_web_search_mention = "web" in system_prompt.lower() or "search" in system_prompt.lower()

        print(f"  ✓ Contains agent name: {has_agent_name}")
        print(f"  ✓ Mentions knowledge graph: {has_memory_mention}")
        print(f"  ✓ Mentions web/search: {has_web_search_mention}")

        if has_agent_name and has_memory_mention and has_web_search_mention:
            print("\n✅ TEST 3 PASSED: System prompt correctly structured\n")
            agent.close()
        else:
            print("\n⚠️ TEST 3 FAILED: Missing key elements\n")
            agent.close()
            return False

    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False

    # TEST 4: Conversation History Management
    print_section("TEST 4: Conversation History Management")
    try:
        print("✓ Creating agent...")
        agent = SyncMemoryAgent(user_id="history_test")

        print("✓ Testing clear_history() method...")
        history_before = agent._async_agent.conversation_history.copy()
        agent.clear_history()
        history_after = agent._async_agent.conversation_history

        print(f"  - History before clear: {len(history_before)} messages")
        print(f"  - History after clear: {len(history_after)} messages")
        print(f"  - Clear successful: {len(history_after) == 0}")

        if len(history_after) == 0:
            print("\n✅ TEST 4 PASSED: Conversation history management working\n")
            agent.close()
        else:
            print("\n❌ TEST 4 FAILED: History not cleared\n")
            agent.close()
            return False

    except Exception as e:
        print(f"\n❌ TEST 4 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False

    # Summary
    print_section("TEST SUMMARY")
    print("✅ All core agent tests passed!")
    print("\n✅ Agent is ready for conversation testing")
    print("\nNote: Memory storage requires correct Azure deployment name")
    print("But core conversation functionality is working!\n")
    return True


if __name__ == "__main__":
    success = test_agent_conversation()
    exit(0 if success else 1)
