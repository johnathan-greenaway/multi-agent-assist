# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a full-featured Python package that enables multi-agent AI collaboration between Claude Code and Gemini Code Assist through MCP (Model Context Protocol). The system provides advanced collaboration modes, shared workspace management, context preservation, and intelligent file coordination.

## Development Commands

### Installation and Setup
```bash
# Install package in development mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"

# Initialize workspace
multi-agent-mcp init --workspace ./agent_workspace

# Generate MCP configuration for Claude Code
multi-agent-mcp config --workspace ./agent_workspace
```

### Running the System
```bash
# Start the MCP server
multi-agent-mcp start --workspace ./agent_workspace

# Start monitoring dashboard
mcp-monitor --workspace ./agent_workspace

# Check workspace status
multi-agent-mcp status --workspace ./agent_workspace

# Clean old files
multi-agent-mcp clean --workspace ./agent_workspace --days 7
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=multi_agent_mcp

# Run specific test file
pytest multi_agent_mcp/tests/test_basic_flow.py

# Run examples
python -m multi_agent_mcp.examples.basic_usage
```

## Architecture

### Core Components

1. **MCP Server** (`gemini-mcp.py`): Handles communication between Claude Code and Gemini Code Assist
2. **Monitor** (`monitor.py`): Real-time dashboard for tracking agent interactions
3. **Agent Workspace**: Structured directory for task coordination and findings

### Key Features

- **Rubber Duck Mode**: Claude can consult Gemini when uncertain
- **Pair Programming**: Real-time collaboration between human, Claude, and Gemini
- **Distributed Analysis**: Automatic work distribution for large codebases
- **Consensus Building**: Both agents must agree on critical decisions
- **Devil's Advocate**: One agent challenges the other's proposals

### File Structure

```
agent_workspace/
├── tasks/          # Task files for Gemini to process
├── findings/       # Analysis results from Gemini
├── logs/           # Interaction logs for monitoring
├── context/        # Shared context between agents
└── shared/         # Additional collaboration files
```

## MCP Configuration

To enable multi-agent features, add to your Claude Code MCP settings:

```json
{
  "mcpServers": {
    "gemini": {
      "command": "python3",
      "args": ["./gemini-mcp.py"],
      "env": {}
    }
  }
}
```

## Available Tools

The system provides these MCP tools:

- `analyze_codebase`: Code analysis and pattern detection
- `refactor_code`: Code refactoring based on patterns
- `generate_tests`: Comprehensive test generation
- `architecture_review`: System architecture analysis
- `dependency_audit`: Dependency security and license checks
- `rubber_duck_review`: Collaborative problem-solving when stuck
- `pair_programming_session`: Real-time coding collaboration
- `distributed_analysis`: Large content analysis distribution
- `consensus_mode`: Critical decision agreement
- `devils_advocate`: Challenge proposals to find weaknesses

## Common Usage Patterns

### Security Audit
```
"Use Gemini to perform a comprehensive security audit of our codebase. 
Focus on authentication, input validation, and dependency vulnerabilities."
```

### Architecture Review
```
"Have both agents review our system architecture. Gemini should analyze 
the current structure while you propose improvements."
```

### Collaborative Debugging
```
"I'm stuck on this race condition. Can you rubber duck with Gemini 
to explore different approaches?"
```

## Important Notes

- **Gemini CLI Integration**: Update the `execute_gemini` method in `gemini-mcp.py` to match your actual Gemini CLI command
- **Workspace Location**: The default workspace is `./agent_workspace` but can be customized
- **Monitoring**: Always run `monitor.py` to track agent interactions and progress
- **Task Context**: The system maintains shared context in `agent_workspace/context/agent_context.json`

## Customization

To add new collaboration modes:

1. Add tool definition in `list_tools()` method
2. Implement handler in `call_tool()` method
3. Create task formatter in `format_task_instructions()`
4. Update monitoring dashboard if needed

## Troubleshooting

- **MCP Server Not Found**: Verify path in Claude Code settings and file permissions
- **Gemini Commands Failing**: Update command in `execute_gemini()` method
- **No Tasks Appearing**: Check workspace directory exists and permissions
- **Performance Issues**: Adjust refresh rate in monitor or workspace location