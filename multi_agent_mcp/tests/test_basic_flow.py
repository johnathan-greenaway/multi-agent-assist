"""
Basic workflow tests for multi-agent collaboration.
"""
import pytest
import asyncio
import tempfile
import json
from pathlib import Path

from ..core.mcp_server import MultiAgentMCPServer
from ..workspace.manager import WorkspaceManager, AgentType
from ..agents.context_manager import ContextManager, ContextType


@pytest.fixture
async def temp_workspace():
    """Create temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir) / "test_workspace"
        workspace.mkdir()
        yield workspace


@pytest.fixture
async def mcp_server(temp_workspace):
    """Create MCP server instance."""
    server = MultiAgentMCPServer(str(temp_workspace))
    yield server
    # Cleanup
    server.workspace.cleanup()


@pytest.mark.asyncio
class TestBasicWorkflow:
    """Test basic multi-agent workflows."""
    
    async def test_server_initialization(self, mcp_server):
        """Test server initializes correctly."""
        assert mcp_server.workspace_path.exists()
        assert (mcp_server.workspace_path / 'tasks').exists()
        assert (mcp_server.workspace_path / 'findings').exists()
        assert (mcp_server.workspace_path / 'context').exists()
    
    async def test_tool_listing(self, mcp_server):
        """Test tools are properly listed."""
        tools = mcp_server._list_tools()
        assert 'tools' in tools
        
        tool_names = [tool['name'] for tool in tools['tools']]
        expected_tools = [
            'analyze_codebase',
            'rubber_duck_review',
            'pair_programming_session',
            'get_agent_context',
            'workspace_status'
        ]
        
        for tool in expected_tools:
            assert tool in tool_names
    
    async def test_context_management(self, temp_workspace):
        """Test context manager functionality."""
        context_manager = ContextManager(temp_workspace)
        
        # Add context
        context_id = await context_manager.add_context(
            "claude",
            ContextType.CONVERSATION,
            {"message": "Test message", "topic": "testing"},
            tags=["test"],
            importance=7
        )
        
        assert context_id is not None
        
        # Get context
        entries = await context_manager.get_context_for_agent("claude")
        assert len(entries) == 1
        assert entries[0].content["message"] == "Test message"
    
    async def test_workspace_file_operations(self, temp_workspace):
        """Test workspace file operations."""
        workspace = WorkspaceManager(temp_workspace)
        
        # Write file
        test_file = Path("test_file.txt")
        success = await workspace.write_file(
            test_file,
            "Test content",
            AgentType.CLAUDE
        )
        assert success
        
        # Read file
        content = await workspace.read_file(test_file, AgentType.GEMINI)
        assert content == "Test content"
        
        # Check file tracking
        abs_path = temp_workspace / test_file
        assert abs_path in workspace.file_metadata
    
    async def test_rubber_duck_workflow(self, mcp_server):
        """Test rubber duck debugging workflow."""
        # Mock Gemini response
        mcp_server.gemini.chat_with_context = lambda *args, **kwargs: asyncio.create_task(
            self._mock_gemini_response("I understand your problem. Have you considered...")
        )
        
        result = await mcp_server._handle_rubber_duck({
            "problem_description": "I'm stuck on this algorithm",
            "attempted_solutions": ["Tried recursion", "Tried iteration"],
            "thinking_mode": "algorithm"
        }, "test_task")
        
        assert result["success"]
        assert "gemini_perspective" in result
        assert result["thinking_mode"] == "algorithm"
    
    async def test_task_handoff(self, mcp_server):
        """Test task handoff between agents."""
        result = await mcp_server._handle_task_handoff({
            "task_description": "Analyze this code for bugs",
            "context_to_share": {"current_file": "test.py"},
            "expected_output": "List of potential bugs"
        }, "handoff_test")
        
        assert result["success"]
        assert result["handoff_created"]
        assert "task_file" in result
        
        # Check task file was created
        task_file = Path(result["task_file"])
        assert task_file.exists()
    
    async def test_workspace_status(self, mcp_server):
        """Test workspace status reporting."""
        result = await mcp_server._handle_workspace_status({
            "include_file_list": True,
            "include_recent_changes": True
        }, "status_test")
        
        assert result["success"]
        assert "workspace_root" in result
        assert "agent_activity" in result
        assert "files" in result
    
    async def test_context_preservation(self, mcp_server):
        """Test context is preserved across operations."""
        # Add some context
        await mcp_server.context.add_context(
            "claude",
            ContextType.TASK,
            {"description": "Working on feature X"},
            importance=8
        )
        
        # Update agent memory
        await mcp_server.context.update_agent_memory(
            "claude",
            current_task="Feature development",
            understanding_update={"architecture": "microservices"},
            new_uncertainty="How to handle scaling?"
        )
        
        # Get context
        result = await mcp_server._handle_get_context({
            "include_peer_questions": True
        }, "context_test")
        
        assert result["success"]
        assert "shared_understanding" in result
        assert result["shared_understanding"]["current_tasks"]["claude"] == "Feature development"
    
    async def _mock_gemini_response(self, content):
        """Mock Gemini response for testing."""
        from ..core.gemini_wrapper import GeminiResponse
        return GeminiResponse(
            success=True,
            content=content,
            metadata={"mock": True}
        )


@pytest.mark.asyncio
class TestAdvancedWorkflows:
    """Test advanced collaboration patterns."""
    
    async def test_distributed_analysis(self, mcp_server):
        """Test distributed analysis workflow."""
        # Create some test files
        test_files = ["file1.py", "file2.js", "file3.md"]
        for filename in test_files:
            await mcp_server.workspace.write_file(
                Path(filename),
                f"# Content of {filename}",
                AgentType.CLAUDE
            )
        
        result = await mcp_server._handle_distributed_analysis({
            "content_paths": test_files,
            "analysis_goals": ["find_bugs", "check_style"],
            "split_strategy": "by_type"
        }, "dist_test")
        
        assert result["success"]
        assert "distribution" in result
        assert len(result["distribution"]["claude"]) + len(result["distribution"]["gemini"]) == len(test_files)
    
    async def test_consensus_building(self, mcp_server):
        """Test consensus building between agents."""
        # Mock Gemini response
        mcp_server.gemini.chat_with_context = lambda *args, **kwargs: asyncio.create_task(
            self._mock_gemini_response("I agree with option 2 because...")
        )
        
        result = await mcp_server._handle_consensus_mode({
            "decision_type": "architecture_choice",
            "options": [
                {"name": "microservices", "pros": ["scalable"], "cons": ["complex"]},
                {"name": "monolith", "pros": ["simple"], "cons": ["not scalable"]}
            ],
            "claude_position": {"preferred": "microservices", "reasoning": "Better for growth"},
            "evaluation_criteria": ["scalability", "maintainability", "complexity"]
        }, "consensus_test")
        
        assert result["success"]
        assert result["decision_type"] == "architecture_choice"
        assert "gemini_evaluation" in result
    
    async def _mock_gemini_response(self, content):
        """Mock Gemini response for testing."""
        from ..core.gemini_wrapper import GeminiResponse
        return GeminiResponse(
            success=True,
            content=content,
            metadata={"mock": True}
        )