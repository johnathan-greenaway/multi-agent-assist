# Claude-Gemini Multi-Agent Setup Guide

## Quick Start

### 1. Installation

```bash
# Clone or create project directory
mkdir claude-gemini-agents
cd claude-gemini-agents

# Install Python dependencies
pip install rich asyncio

# Create the MCP server file
# Copy the gemini_mcp_server.py content into this file

# Create the monitor file  
# Copy the monitor.py content into this file

# Make them executable
chmod +x gemini_mcp_server.py monitor.py
```

### 2. Configure Claude Code

Add to your Claude Code MCP settings (usually in `~/.config/claude-code/mcp.json` or similar):

```json
{
  "mcpServers": {
    "gemini": {
      "command": "python3",
      "args": ["/path/to/gemini_mcp_server.py"],
      "env": {}
    }
  }
}
```

### 3. Adjust for Your Gemini CLI

In `gemini_mcp_server.py`, update the `execute_gemini` method (around line 380) to match your actual Gemini command:

```python
# Replace this section with your actual Gemini CLI
cmd = [
    "gemini-code-assist",  # Your actual Gemini command
    "analyze",
    f"--task={task_file}",
    f"--output={findings_file}"
]

# Actually run the subprocess
process = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)
stdout, stderr = await process.communicate()
```

### 4. Start Monitoring

In a separate terminal:

```bash
# Start the monitoring dashboard
python monitor.py

# Or watch a specific file
python monitor.py --watch agent_workspace/context/agent_context.json

# Custom workspace location
python monitor.py --workspace /path/to/workspace --refresh 0.5
```

## Usage Examples

### Example 1: Security Audit

Tell Claude Code:
```
"Hey Claude, can you use Gemini to perform a comprehensive security audit of our codebase? 
Focus on authentication, input validation, and dependency vulnerabilities. 
Then create a remediation plan based on the findings."
```

Claude will:
1. Create a security audit task for Gemini
2. Monitor Gemini's progress
3. Analyze the findings
4. Create a remediation plan
5. Coordinate any fixes

### Example 2: Architecture Review

```
"I need both of you to review our system architecture. 
Have Gemini analyze the current structure and identify bottlenecks, 
while you focus on proposing improvements. 
Let's create a comprehensive architecture document together."
```

### Example 3: Test Generation

```
"Use Gemini to generate comprehensive unit tests for our API endpoints. 
After Gemini creates them, review the tests and add any edge cases it might have missed."
```

### Example 4: Parallel Analysis

```
"While I'm discussing the API design with you, 
have Gemini analyze our database queries for N+1 problems and optimization opportunities. 
We'll combine both findings into an optimization plan."
```

## Monitoring Features

### Dashboard View
- **Summary Panel**: Shows active/completed task counts
- **Task Table**: Recent tasks with status, duration, and findings
- **Latest Findings**: Executive summaries from recent analyses
- **Agent Context**: Current ongoing tasks

### File Watching
Watch specific files for real-time updates:
```bash
# Watch the context file
python monitor.py --watch agent_workspace/context/agent_context.json

# Watch a specific task
python monitor.py --watch agent_workspace/tasks/abc123_analyze_codebase.md

# Watch findings as they're generated
python monitor.py --watch agent_workspace/findings/abc123_findings.md
```

## Advanced Usage

### 1. Custom Tools

Add new tools to `list_tools()` in the MCP server:

```python
{
    "name": "custom_analysis",
    "description": "Custom analysis tool",
    "inputSchema": {
        "type": "object",
        "properties": {
            "analysis_type": {"type": "string"},
            "parameters": {"type": "object"}
        }
    }
}
```

### 2. Inter-Agent Communication

Agents communicate through:
- **Task Files**: Instructions from Claude to Gemini
- **Findings Files**: Results from Gemini to Claude
- **Context File**: Shared state and ongoing work
- **Shared Directory**: Additional files for collaboration

### 3. Error Handling

The system includes:
- Automatic retry logic
- Timeout handling
- Error logging
- Graceful degradation

## Troubleshooting

### Common Issues

1. **MCP Server Not Found**
   - Verify the path in Claude Code settings
   - Check file permissions
   - Ensure Python 3.7+ is installed

2. **Gemini Commands Failing**
   - Update the command in `execute_gemini()`
   - Check Gemini CLI is in PATH
   - Verify Gemini has necessary permissions

3. **No Tasks Appearing**
   - Check workspace directory exists
   - Verify Claude Code is configured correctly
   - Look for errors in Claude Code logs

### Debug Mode

Enable debug logging by setting environment variable:
```bash
export GEMINI_MCP_DEBUG=1
```

## Best Practices

1. **Clear Task Descriptions**: Be specific about what you want each agent to do
2. **Monitor Progress**: Keep the dashboard open to track ongoing work
3. **Review Findings**: Always review findings marked with `[CLAUDE-REVIEW]`
4. **Iterative Refinement**: Use the findings from one task to inform the next
5. **Context Preservation**: Let Claude maintain high-level context while Gemini handles details

## Security Notes

- All files are stored locally in the workspace directory
- No data is sent to external services (except through Gemini itself)
- Sensitive findings should be reviewed before sharing
- Consider encrypting the workspace directory for sensitive projects

## Next Steps

1. Customize the tools for your specific workflow
2. Add more sophisticated error handling
3. Create project-specific templates
4. Build a web interface for easier monitoring
5. Add support for more AI assistants (GitHub Copilot, etc.)