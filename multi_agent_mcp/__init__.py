"""
Multi-Agent MCP: Collaborative AI Development System

A system enabling Claude Code to orchestrate Gemini Code Assist through MCP,
with shared workspaces, context preservation, and advanced collaboration modes.
"""

__version__ = "0.1.0"

from .core.mcp_server import MultiAgentMCPServer
from .core.gemini_wrapper import GeminiWrapper
from .workspace.manager import WorkspaceManager
from .agents.context_manager import ContextManager

__all__ = [
    "MultiAgentMCPServer",
    "GeminiWrapper", 
    "WorkspaceManager",
    "ContextManager",
]