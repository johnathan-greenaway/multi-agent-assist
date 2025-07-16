# Multi-Agent MCP System

A comprehensive Python package that enables Claude Code to orchestrate Gemini Code Assist through MCP (Model Context Protocol), featuring advanced multi-agent collaboration modes, shared workspaces, context preservation, and intelligent file coordination.

## 🚀 Features

### Core Capabilities
- **Native Gemini Integration**: Direct wrapper for Gemini Code Assist CLI with sandbox support
- **Shared Workspace Management**: File locking, change tracking, and conflict resolution
- **Context Preservation**: Persistent memory and understanding between agents
- **Real-time Monitoring**: Comprehensive dashboard for tracking agent interactions

### Advanced Collaboration Modes
- **Rubber Duck Mode**: Claude can consult Gemini when uncertain
- **Pair Programming**: Real-time collaborative coding sessions
- **Distributed Analysis**: Automatic work distribution for large codebases
- **Consensus Building**: Both agents must agree on critical decisions
- **Devil's Advocate**: One agent challenges the other's proposals
- **Sandbox Execution**: Safe code execution in isolated environments

## 📦 Installation

### From Source
```bash
git clone https://github.com/johnathan-greenaway/multi-agent-assist/
cd multi-agent-assist
pip install -e .
```

### Development Installation
```bash
pip install -e ".[dev]"
```

## 🛠️ Setup

### 1. Initialize Workspace
```bash
# Create and initialize workspace
multi-agent-mcp init --workspace ./my_workspace

# Check status
multi-agent-mcp status --workspace ./my_workspace
```

### 2. Configure Claude Code
```bash
# Generate MCP configuration
multi-agent-mcp config --workspace ./my_workspace --output mcp_config.json
```

Add the generated configuration to your Claude Code settings:

```json
{
  "mcpServers": {
    "multi-agent": {
      "command": "python",
      "args": ["-m", "multi_agent_mcp.core.mcp_server"],
      "env": {
        "WORKSPACE_PATH": "/path/to/your/workspace"
      }
    }
  }
}
```

### 3. Start the System
```bash
# Start MCP server
multi-agent-mcp start --workspace ./my_workspace

# In another terminal, start monitoring
mcp-monitor --workspace ./my_workspace
```

## 💡 Usage Examples

### Basic Codebase Analysis
```
"Hey Claude, use Gemini to analyze our codebase for security vulnerabilities. 
Focus on authentication and input validation patterns."
```

### Rubber Duck Debugging
```
"I'm stuck on this React infinite re-render issue. Can you rubber duck with 
Gemini to explore different approaches?"
```

### Pair Programming
```
"Let's start a pair programming session to implement JWT authentication. 
Have Gemini monitor for issues while we work on the auth service."
```

### Distributed Analysis
```
"We have a large codebase to analyze. Can you and Gemini split the work? 
You handle architecture review while Gemini checks for performance issues."
```

### Consensus Building
```
"We need to choose between PostgreSQL and MongoDB. Both of you evaluate 
the options and reach a consensus based on our scalability requirements."
```

## 🏗️ Architecture

### Components

```
multi_agent_mcp/
├── core/
│   ├── mcp_server.py      # Main MCP protocol handler
│   └── gemini_wrapper.py  # Native Gemini CLI wrapper
├── workspace/
│   └── manager.py         # File coordination and locking
├── agents/
│   └── context_manager.py # Memory and context preservation
├── monitor.py             # Real-time monitoring dashboard
└── cli.py                 # Command-line interface
```

### Workspace Structure

```
agent_workspace/
├── tasks/                 # Task coordination files
├── findings/              # Analysis results
├── context/               # Shared memory and understanding
├── shared/                # Cross-agent collaboration files
├── claude_workspace/      # Claude-specific files
├── gemini_workspace/      # Gemini-specific files
├── sandbox/               # Safe execution environment
├── logs/                  # Event and interaction logs
└── history/               # File change history
```

## 🔧 Advanced Features

### File Coordination
- **Automatic Locking**: Prevents conflicts during concurrent access
- **Change Tracking**: Maintains history of all modifications
- **Conflict Detection**: Identifies and resolves editing conflicts

### Context Management
- **Persistent Memory**: Agents remember across sessions
- **Shared Understanding**: Cross-agent knowledge base
- **Question Tracking**: Peer-to-peer inquiry system

### Sandbox Execution
- **Safe Code Running**: Execute code in isolated environment
- **Artifact Collection**: Capture execution outputs
- **Resource Limiting**: Prevent runaway processes

### Monitoring & Observability
- **Real-time Dashboard**: Live view of agent activity
- **Event Logging**: Comprehensive audit trail
- **Performance Metrics**: Task completion and timing stats

## 📊 Monitoring Dashboard

The monitoring dashboard provides real-time insights:

```bash
mcp-monitor --workspace ./my_workspace
```

Features:
- **Task Overview**: Current and completed tasks
- **Agent Status**: Memory, uncertainties, and questions
- **File Activity**: Real-time file operations
- **Collaboration State**: Shared understanding and decisions

## 🧪 Testing

```bash
# Run tests
pytest multi_agent_mcp/tests/

# Run with coverage
pytest --cov=multi_agent_mcp

# Run specific test
pytest multi_agent_mcp/tests/test_basic_flow.py::TestBasicWorkflow::test_rubber_duck_workflow
```

## 📚 Examples

See `multi_agent_mcp/examples/` for comprehensive examples:

```bash
# Run basic usage examples
python -m multi_agent_mcp.examples.basic_usage
```

## 🛡️ Security Considerations

- All operations are performed locally in the workspace
- Sandbox execution is isolated and resource-limited
- File access is controlled through locking mechanisms
- No external network access except through configured tools

## 🚧 Development

### Project Structure
```bash
# Install development dependencies
pip install -e ".[dev]"

# Run linting
black multi_agent_mcp/
mypy multi_agent_mcp/

# Build package
python setup.py sdist bdist_wheel
```

### Adding New Tools

1. Add tool definition to `MultiAgentMCPServer._list_tools()`
2. Implement handler method `_handle_your_tool()`
3. Add routing in `_call_tool()`
4. Write tests in `tests/`

### Extending Gemini Integration

The `GeminiWrapper` class can be extended to support additional Gemini CLI features:

```python
async def your_custom_gemini_operation(self, args):
    cmd = [self.command, "your-operation", ...args]
    return await self._execute_command(cmd, GeminiMode.NORMAL)
```

## 📖 Documentation

- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api.md)
- [Collaboration Patterns](docs/patterns.md)
- [Troubleshooting](docs/troubleshooting.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: Report bugs and request features on GitHub
- **Documentation**: Check the `docs/` directory
- **Examples**: See `examples/` for usage patterns

## 🎯 Roadmap

- [ ] Web-based monitoring interface
- [ ] Support for additional AI assistants
- [ ] Advanced conflict resolution algorithms
- [ ] Performance optimization tools
- [ ] Integration with popular IDEs

---

**Built with ❤️ for the AI-powered development community**
