# Claude-Gemini Multi-Agent System Architecture

## Overview
A system where Claude Code orchestrates Gemini Code Assist through MCP (Model Context Protocol), enabling collaborative AI-powered development with full visibility into inter-agent communication.

## System Components

### 1. MCP Server for Gemini (`gemini_mcp_server.py`)
```python
#!/usr/bin/env python3
import json
import subprocess
import os
import asyncio
from datetime import datetime
from pathlib import Path
import sys

class GeminiMCPServer:
    def __init__(self, workspace_dir="./agent_workspace"):
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(exist_ok=True)
        self.task_dir = self.workspace_dir / "tasks"
        self.findings_dir = self.workspace_dir / "findings"
        self.logs_dir = self.workspace_dir / "logs"
        
        for dir in [self.task_dir, self.findings_dir, self.logs_dir]:
            dir.mkdir(exist_ok=True)
    
    async def handle_request(self, request):
        """Main MCP request handler"""
        method = request.get("method")
        params = request.get("params", {})
        
        if method == "tools/list":
            return self.list_tools()
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            return await self.call_tool(tool_name, arguments)
        
    def list_tools(self):
        """Return available tools for MCP"""
        return {
            "tools": [
                {
                    "name": "analyze_codebase",
                    "description": "Analyze codebase for patterns, issues, or specific queries",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "focus_areas": {"type": "array", "items": {"type": "string"}},
                            "task_id": {"type": "string"}
                        },
                        "required": ["query", "task_id"]
                    }
                },
                {
                    "name": "refactor_code",
                    "description": "Refactor code based on patterns or requirements",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "instructions": {"type": "string"},
                            "files": {"type": "array", "items": {"type": "string"}},
                            "task_id": {"type": "string"}
                        },
                        "required": ["instructions", "task_id"]
                    }
                },
                {
                    "name": "scan_dependencies",
                    "description": "Scan and analyze project dependencies",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "check_security": {"type": "boolean"},
                            "check_updates": {"type": "boolean"},
                            "task_id": {"type": "string"}
                        },
                        "required": ["task_id"]
                    }
                }
            ]
        }
    
    async def call_tool(self, tool_name, arguments):
        """Execute tool and return results"""
        task_id = arguments.get("task_id")
        timestamp = datetime.now().isoformat()
        
        # Log the interaction
        log_entry = {
            "timestamp": timestamp,
            "tool": tool_name,
            "arguments": arguments,
            "status": "started"
        }
        self.log_interaction(task_id, log_entry)
        
        # Create task file for Gemini
        task_file = self.task_dir / f"{task_id}.md"
        self.create_task_file(task_file, tool_name, arguments)
        
        # Execute Gemini command
        result = await self.execute_gemini(tool_name, task_file, task_id)
        
        # Log completion
        log_entry["status"] = "completed"
        log_entry["result_file"] = str(self.findings_dir / f"{task_id}_findings.md")
        self.log_interaction(task_id, log_entry)
        
        return result
    
    def create_task_file(self, task_file, tool_name, arguments):
        """Create markdown task file for Gemini to process"""
        content = f"""# Task: {tool_name}
**Task ID**: {arguments.get('task_id')}
**Timestamp**: {datetime.now().isoformat()}

## Instructions
{self.format_task_instructions(tool_name, arguments)}

## Expected Output
Please write your findings to: `findings/{arguments.get('task_id')}_findings.md`

Format your output with clear sections:
- Summary
- Detailed Findings
- Recommendations
- Code Examples (if applicable)
"""
        task_file.write_text(content)
    
    def format_task_instructions(self, tool_name, arguments):
        """Format tool-specific instructions"""
        if tool_name == "analyze_codebase":
            return f"""
Analyze the codebase with the following query:
**Query**: {arguments.get('query')}

Focus on these areas:
{chr(10).join(f"- {area}" for area in arguments.get('focus_areas', []))}
"""
        elif tool_name == "refactor_code":
            return f"""
Refactor the following files according to these instructions:
**Instructions**: {arguments.get('instructions')}

Target files:
{chr(10).join(f"- {file}" for file in arguments.get('files', []))}
"""
        elif tool_name == "scan_dependencies":
            return f"""
Scan project dependencies with these checks:
- Security vulnerabilities: {arguments.get('check_security', True)}
- Available updates: {arguments.get('check_updates', True)}
"""
    
    async def execute_gemini(self, tool_name, task_file, task_id):
        """Execute Gemini command and capture output"""
        findings_file = self.findings_dir / f"{task_id}_findings.md"
        
        # Construct Gemini command
        # Adjust this based on your Gemini CLI interface
        cmd = [
            "gemini-code-assist",  # or whatever the CLI command is
            "process",
            "--task", str(task_file),
            "--output", str(findings_file)
        ]
        
        try:
            # Run Gemini
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            # Read the findings
            if findings_file.exists():
                findings = findings_file.read_text()
                return {
                    "success": True,
                    "findings": findings,
                    "findings_file": str(findings_file)
                }
            else:
                return {
                    "success": False,
                    "error": "Findings file not created",
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode()
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def log_interaction(self, task_id, log_entry):
        """Log interactions for monitoring"""
        log_file = self.logs_dir / f"{task_id}_log.json"
        
        logs = []
        if log_file.exists():
            logs = json.loads(log_file.read_text())
        
        logs.append(log_entry)
        log_file.write_text(json.dumps(logs, indent=2))

# MCP Server startup
async def main():
    server = GeminiMCPServer()
    
    # Read from stdin, write to stdout (MCP protocol)
    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
                
            request = json.loads(line)
            response = await server.handle_request(request)
            
            print(json.dumps(response))
            sys.stdout.flush()
            
        except Exception as e:
            error_response = {
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
            print(json.dumps(error_response))
            sys.stdout.flush()

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Claude Code Integration Instructions

To use this system through Claude Code:

1. **Setup the MCP server configuration** in your Claude Code settings:

```json
{
  "mcpServers": {
    "gemini": {
      "command": "python",
      "args": ["./gemini_mcp_server.py"],
      "env": {}
    }
  }
}
```

2. **Usage Pattern** - Just talk naturally to Claude Code:

```
"Hey Claude, can you use Gemini to analyze this codebase for security vulnerabilities, 
then based on what it finds, create a remediation plan?"
```

Claude Code will:
- Create a task in the shared workspace
- Invoke Gemini through MCP
- Monitor the findings
- Synthesize and respond

### 3. Monitoring Dashboard (`monitor.py`)

```python
#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime
import time
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel

class AgentMonitor:
    def __init__(self, workspace_dir="./agent_workspace"):
        self.workspace_dir = Path(workspace_dir)
        self.console = Console()
    
    def get_recent_tasks(self, limit=10):
        """Get recent tasks from both agents"""
        tasks = []
        
        # Scan task directory
        task_dir = self.workspace_dir / "tasks"
        for task_file in sorted(task_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
            task_id = task_file.stem
            content = task_file.read_text()
            
            # Get corresponding log
            log_file = self.workspace_dir / "logs" / f"{task_id}_log.json"
            status = "pending"
            if log_file.exists():
                logs = json.loads(log_file.read_text())
                if logs:
                    status = logs[-1].get("status", "unknown")
            
            tasks.append({
                "id": task_id,
                "file": task_file.name,
                "status": status,
                "created": datetime.fromtimestamp(task_file.stat().st_mtime)
            })
        
        return tasks
    
    def create_dashboard(self):
        """Create monitoring dashboard"""
        layout = Layout()
        
        # Get recent tasks
        tasks = self.get_recent_tasks()
        
        # Create tasks table
        table = Table(title="Recent Agent Tasks")
        table.add_column("Task ID", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Created", style="yellow")
        
        for task in tasks:
            status_style = "green" if task["status"] == "completed" else "yellow"
            table.add_row(
                task["id"],
                task["status"],
                task["created"].strftime("%Y-%m-%d %H:%M:%S")
            )
        
        # Create summary panel
        summary = Panel(
            f"Active Tasks: {sum(1 for t in tasks if t['status'] == 'started')}\n"
            f"Completed: {sum(1 for t in tasks if t['status'] == 'completed')}\n"
            f"Total Tasks: {len(tasks)}",
            title="Summary"
        )
        
        layout.split_column(
            Layout(summary, size=6),
            Layout(table)
        )
        
        return layout
    
    def run_live_monitor(self):
        """Run live monitoring dashboard"""
        with Live(self.create_dashboard(), refresh_per_second=1) as live:
            while True:
                time.sleep(1)
                live.update(self.create_dashboard())

if __name__ == "__main__":
    monitor = AgentMonitor()
    monitor.run_live_monitor()
```

### 4. Example Workflow Script

```python
# example_workflow.py
"""
Example of how Claude Code would orchestrate Gemini
"""

async def security_audit_workflow(project_path):
    """Full security audit using both agents"""
    
    # Step 1: Gemini analyzes codebase
    gemini_task = {
        "name": "analyze_codebase",
        "arguments": {
            "query": "Identify security vulnerabilities and unsafe patterns",
            "focus_areas": ["auth", "data_validation", "dependencies"],
            "task_id": f"security_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
    }
    
    # Claude Code invokes Gemini via MCP
    findings = await mcp_client.call_tool(gemini_task)
    
    # Step 2: Claude analyzes findings and creates remediation plan
    # Step 3: Gemini implements fixes
    # Step 4: Claude validates changes
    
    return audit_report
```

## Setup Instructions

1. **Install Dependencies**:
```bash
pip install rich asyncio pathlib
```

2. **Configure Claude Code**:
- Add the MCP server configuration to your Claude Code settings
- Ensure the workspace directory is accessible

3. **Start Monitoring**:
```bash
python monitor.py
```

4. **Use Natural Language**:
Just tell Claude Code what you want, mentioning when you'd like Gemini's help:
- "Use Gemini to scan for security issues"
- "Have Gemini analyze the architecture while you focus on the API design"
- "Get Gemini to refactor the database layer based on these patterns"

## Benefits

1. **Context Preservation**: Claude maintains high-level context while Gemini handles specific tasks
2. **Parallel Processing**: Both agents can work simultaneously
3. **Full Visibility**: All interactions logged and monitorable
4. **Natural Interface**: Just talk to Claude Code normally
5. **Audit Trail**: Complete history of all agent interactions

## Next Steps

1. Adjust the `execute_gemini` method to match your actual Gemini CLI
2. Add more tool types based on your needs
3. Implement error handling and retry logic
4. Create visualization tools for the interaction logs
5. Add web-based monitoring interface