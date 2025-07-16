"""
Basic usage examples for the Multi-Agent MCP system.
"""
import asyncio
import json
from pathlib import Path

from ..core.mcp_server import MultiAgentMCPServer


async def basic_codebase_analysis():
    """Example: Basic codebase analysis with Gemini."""
    # Initialize server
    server = MultiAgentMCPServer("./example_workspace")
    
    # Simulate MCP call from Claude Code
    request = {
        "method": "tools/call",
        "params": {
            "name": "analyze_codebase",
            "arguments": {
                "query": "Find potential security vulnerabilities",
                "focus_areas": ["authentication", "input_validation", "sql_injection"],
                "include_patterns": ["*.py", "*.js"],
                "exclude_patterns": ["tests/*", "node_modules/*"]
            }
        }
    }
    
    print("🔍 Starting codebase analysis...")
    response = await server.handle_request(request)
    
    if response.get("success"):
        print("✅ Analysis completed!")
        print(f"📁 Findings saved to: {response['findings_file']}")
        print(f"⏱️  Execution time: {response['execution_time']:.2f}s")
    else:
        print("❌ Analysis failed:", response.get("error"))
    
    return response


async def rubber_duck_debugging():
    """Example: Rubber duck debugging session."""
    server = MultiAgentMCPServer("./example_workspace")
    
    request = {
        "method": "tools/call",
        "params": {
            "name": "rubber_duck_review",
            "arguments": {
                "problem_description": "My React component is re-rendering infinitely",
                "attempted_solutions": [
                    "Added useCallback to event handlers",
                    "Memoized child components",
                    "Checked dependency arrays"
                ],
                "code_context": """
                const MyComponent = () => {
                    const [data, setData] = useState([]);
                    
                    useEffect(() => {
                        fetchData().then(setData);
                    }, [data]); // Problem might be here?
                    
                    return <div>{data.map(item => <Item key={item.id} data={item} />)}</div>;
                };
                """,
                "specific_questions": [
                    "Is the useEffect dependency array causing the issue?",
                    "Should I be using useRef instead?",
                    "What's the best pattern for this scenario?"
                ],
                "thinking_mode": "debug"
            }
        }
    }
    
    print("🦆 Starting rubber duck session...")
    response = await server.handle_request(request)
    
    if response.get("success"):
        print("✅ Rubber duck session completed!")
        print("\n🤖 Gemini's perspective:")
        print(response["gemini_perspective"])
    else:
        print("❌ Session failed:", response.get("error"))
    
    return response


async def pair_programming_session():
    """Example: Pair programming session setup."""
    server = MultiAgentMCPServer("./example_workspace")
    
    request = {
        "method": "tools/call",
        "params": {
            "name": "pair_programming_session",
            "arguments": {
                "session_type": "feature_development",
                "objective": "Implement user authentication with JWT tokens",
                "current_file": "src/auth/auth.service.ts",
                "sync_interval": 30
            }
        }
    }
    
    print("👥 Starting pair programming session...")
    response = await server.handle_request(request)
    
    if response.get("success"):
        print("✅ Pair programming session initialized!")
        print(f"📄 Session file: {response['session_file']}")
        print("🔄 Both agents can now collaborate on the objective")
    else:
        print("❌ Session setup failed:", response.get("error"))
    
    return response


async def consensus_decision_making():
    """Example: Consensus decision making between agents."""
    server = MultiAgentMCPServer("./example_workspace")
    
    request = {
        "method": "tools/call",
        "params": {
            "name": "consensus_mode",
            "arguments": {
                "decision_type": "database_choice",
                "options": [
                    {
                        "name": "PostgreSQL",
                        "pros": ["ACID compliance", "JSON support", "mature ecosystem"],
                        "cons": ["higher resource usage", "complex setup"]
                    },
                    {
                        "name": "MongoDB",
                        "pros": ["flexible schema", "horizontal scaling", "JSON native"],
                        "cons": ["eventual consistency", "memory usage"]
                    },
                    {
                        "name": "SQLite",
                        "pros": ["simple", "embedded", "no server needed"],
                        "cons": ["limited concurrency", "not suitable for production scale"]
                    }
                ],
                "claude_position": {
                    "preferred": "PostgreSQL",
                    "reasoning": "Best balance of features and reliability for our use case",
                    "concerns": "Might be overkill for the current scale"
                },
                "evaluation_criteria": [
                    "scalability",
                    "development speed",
                    "operational complexity",
                    "data consistency",
                    "ecosystem support"
                ]
            }
        }
    }
    
    print("🤝 Starting consensus building...")
    response = await server.handle_request(request)
    
    if response.get("success"):
        print("✅ Consensus process initiated!")
        print(f"📊 Decision type: {response['decision_type']}")
        print("\n🤖 Gemini's evaluation:")
        print(response["gemini_evaluation"])
    else:
        print("❌ Consensus process failed:", response.get("error"))
    
    return response


async def workspace_management_demo():
    """Example: Workspace management and status."""
    server = MultiAgentMCPServer("./example_workspace")
    
    # Get workspace status
    status_request = {
        "method": "tools/call",
        "params": {
            "name": "workspace_status",
            "arguments": {
                "include_file_list": True,
                "include_recent_changes": True
            }
        }
    }
    
    print("📊 Getting workspace status...")
    status_response = await server.handle_request(status_request)
    
    if status_response.get("success"):
        print("✅ Workspace status retrieved!")
        print(f"📁 Workspace root: {status_response['workspace_root']}")
        print("\n🤖 Agent activity:")
        for agent, activity in status_response["agent_activity"].items():
            print(f"   {agent}: {activity['active_files']} files, last active: {activity['last_active']}")
    
    # Get agent context
    context_request = {
        "method": "tools/call",
        "params": {
            "name": "get_agent_context",
            "arguments": {
                "include_peer_questions": True,
                "context_types": ["conversation", "task", "findings"]
            }
        }
    }
    
    print("\n🧠 Getting agent context...")
    context_response = await server.handle_request(context_request)
    
    if context_response.get("success"):
        print("✅ Context retrieved!")
        print(f"📝 Context entries: {len(context_response['context_entries'])}")
        
        understanding = context_response["shared_understanding"]
        claude_task = understanding["current_tasks"].get("claude")
        gemini_task = understanding["current_tasks"].get("gemini")
        
        if claude_task:
            print(f"🔵 Claude current task: {claude_task}")
        if gemini_task:
            print(f"🟢 Gemini current task: {gemini_task}")
    
    return status_response, context_response


async def distributed_analysis_demo():
    """Example: Distributed analysis of large codebase."""
    server = MultiAgentMCPServer("./example_workspace")
    
    # Create some example files first
    workspace_path = Path("./example_workspace")
    example_files = [
        "src/components/Header.tsx",
        "src/services/api.service.ts",
        "src/utils/validation.py",
        "backend/models/user.py",
        "backend/controllers/auth.py",
        "docs/README.md",
        "tests/unit/auth.test.js"
    ]
    
    # Simulate large codebase
    for file_path in example_files:
        full_path = workspace_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(f"// Example content for {file_path}")
    
    request = {
        "method": "tools/call",
        "params": {
            "name": "distributed_analysis",
            "arguments": {
                "content_paths": example_files,
                "analysis_goals": [
                    "identify_security_issues",
                    "check_code_quality",
                    "find_performance_bottlenecks",
                    "verify_test_coverage"
                ],
                "split_strategy": "by_type"
            }
        }
    }
    
    print("🔄 Starting distributed analysis...")
    response = await server.handle_request(request)
    
    if response.get("success"):
        print("✅ Distributed analysis initiated!")
        print("\n📊 Work distribution:")
        print(f"🔵 Claude assigned: {len(response['distribution']['claude'])} files")
        for file in response['distribution']['claude']:
            print(f"   - {file}")
        
        print(f"\n🟢 Gemini assigned: {len(response['distribution']['gemini'])} files")
        for file in response['distribution']['gemini']:
            print(f"   - {file}")
        
        if response.get("gemini_analysis", {}).get("success"):
            print("\n🤖 Gemini analysis completed!")
            print(f"📝 Files analyzed: {response['gemini_analysis']['files_analyzed']}")
    else:
        print("❌ Distributed analysis failed:", response.get("error"))
    
    return response


async def main():
    """Run all examples."""
    print("🚀 Multi-Agent MCP System Examples")
    print("=" * 50)
    
    examples = [
        ("Basic Codebase Analysis", basic_codebase_analysis),
        ("Rubber Duck Debugging", rubber_duck_debugging),
        ("Pair Programming Session", pair_programming_session),
        ("Consensus Decision Making", consensus_decision_making),
        ("Workspace Management", workspace_management_demo),
        ("Distributed Analysis", distributed_analysis_demo)
    ]
    
    for name, example_func in examples:
        print(f"\n🔧 Running: {name}")
        print("-" * 30)
        try:
            await example_func()
        except Exception as e:
            print(f"❌ Example failed: {e}")
        
        print("\n" + "="*50)
    
    print("✅ All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())