#!/usr/bin/env python3
"""
Gemini MCP Server - Allows Claude Code to orchestrate Gemini Code Assist
"""
import json
import subprocess
import os
import asyncio
from datetime import datetime
from pathlib import Path
import sys
import uuid
import shutil

class GeminiMCPServer:
    def __init__(self, workspace_dir="./agent_workspace"):
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.dirs = {
            'tasks': self.workspace_dir / "tasks",
            'findings': self.workspace_dir / "findings", 
            'logs': self.workspace_dir / "logs",
            'context': self.workspace_dir / "context",
            'shared': self.workspace_dir / "shared"
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
        
        # Create context file for agents to share state
        self.context_file = self.dirs['context'] / "agent_context.json"
        if not self.context_file.exists():
            self.context_file.write_text(json.dumps({
                "project_info": {},
                "ongoing_tasks": [],
                "completed_tasks": []
            }, indent=2))
    
    async def handle_request(self, request):
        """Main MCP request handler"""
        method = request.get("method")
        params = request.get("params", {})
        
        handlers = {
            "tools/list": self.list_tools,
            "tools/call": lambda: self.call_tool(params.get("name"), params.get("arguments", {})),
            "completion/complete": lambda: self.handle_completion(params)
        }
        
        handler = handlers.get(method)
        if handler:
            if asyncio.iscoroutinefunction(handler):
                return await handler()
            else:
                result = handler()
                if asyncio.iscoroutine(result):
                    return await result
                return result
        else:
            return {"error": {"code": -32601, "message": f"Method not found: {method}"}}
    
    def list_tools(self):
        """Return available tools for MCP"""
        return {
            "tools": [
                {
                    "name": "analyze_codebase",
                    "description": "Use Gemini to analyze codebase for patterns, issues, or specific queries",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "What to analyze"},
                            "focus_areas": {"type": "array", "items": {"type": "string"}, "description": "Specific areas to focus on"},
                            "include_patterns": {"type": "array", "items": {"type": "string"}, "description": "File patterns to include"},
                            "exclude_patterns": {"type": "array", "items": {"type": "string"}, "description": "File patterns to exclude"}
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "refactor_code", 
                    "description": "Use Gemini to refactor code based on patterns or requirements",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "instructions": {"type": "string", "description": "Refactoring instructions"},
                            "files": {"type": "array", "items": {"type": "string"}, "description": "Files to refactor"},
                            "patterns": {"type": "object", "description": "Before/after patterns"},
                            "preserve_tests": {"type": "boolean", "description": "Ensure tests still pass"}
                        },
                        "required": ["instructions"]
                    }
                },
                {
                    "name": "generate_tests",
                    "description": "Use Gemini to generate comprehensive tests",
                    "inputSchema": {
                        "type": "object", 
                        "properties": {
                            "target_files": {"type": "array", "items": {"type": "string"}},
                            "test_type": {"type": "string", "enum": ["unit", "integration", "e2e"]},
                            "coverage_target": {"type": "number", "description": "Target coverage percentage"}
                        },
                        "required": ["target_files"]
                    }
                },
                {
                    "name": "architecture_review",
                    "description": "Use Gemini to review and document system architecture",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "focus": {"type": "string", "enum": ["security", "performance", "scalability", "maintainability", "all"]},
                            "generate_diagrams": {"type": "boolean"},
                            "suggest_improvements": {"type": "boolean"}
                        }
                    }
                },
                {
                    "name": "dependency_audit", 
                    "description": "Use Gemini to audit dependencies for issues",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "check_security": {"type": "boolean"},
                            "check_licenses": {"type": "boolean"},
                            "check_updates": {"type": "boolean"},
                            "generate_sbom": {"type": "boolean", "description": "Generate Software Bill of Materials"}
                        }
                    }
                },
                {
                    "name": "monitor_status",
                    "description": "Get status of ongoing Gemini tasks",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "Specific task ID or 'all' for all tasks"}
                        }
                    }
                },
                {
                    "name": "rubber_duck_review",
                    "description": "Claude Code can use Gemini as a rubber duck when stuck - talk through problems together",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "problem_description": {"type": "string", "description": "Describe what you're stuck on"},
                            "attempted_solutions": {"type": "array", "items": {"type": "string"}, "description": "What you've already tried"},
                            "code_context": {"type": "string", "description": "Relevant code or context"},
                            "specific_questions": {"type": "array", "items": {"type": "string"}, "description": "Specific questions to explore"},
                            "thinking_mode": {
                                "type": "string", 
                                "enum": ["debug", "design", "algorithm", "architecture", "general"],
                                "description": "Type of problem you're stuck on"
                            }
                        },
                        "required": ["problem_description"]
                    }
                },
                {
                    "name": "pair_programming_session",
                    "description": "Start a collaborative coding session with human, Claude, and Gemini",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "session_type": {
                                "type": "string",
                                "enum": ["feature_development", "bug_fixing", "refactoring", "code_review", "design_session"]
                            },
                            "current_file": {"type": "string", "description": "File being worked on"},
                            "objective": {"type": "string", "description": "What we're trying to achieve"},
                            "collaboration_style": {
                                "type": "string",
                                "enum": ["driver_navigator", "mob_programming", "parallel_development", "review_cycle"]
                            },
                            "sync_interval": {"type": "integer", "description": "How often to sync (seconds)", "default": 30}
                        },
                        "required": ["session_type", "objective"]
                    }
                },
                {
                    "name": "distributed_analysis", 
                    "description": "Distribute large content analysis between Claude and Gemini",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "content_type": {"type": "string", "enum": ["codebase", "documentation", "logs", "data", "mixed"]},
                            "content_size": {"type": "integer", "description": "Approximate size in lines/bytes"},
                            "analysis_goals": {"type": "array", "items": {"type": "string"}},
                            "split_strategy": {
                                "type": "string",
                                "enum": ["by_type", "by_module", "by_complexity", "round_robin", "expertise_based"]
                            },
                            "synthesis_required": {"type": "boolean", "default": true}
                        },
                        "required": ["content_type", "analysis_goals"]
                    }
                },
                {
                    "name": "consensus_mode",
                    "description": "Require both agents to agree on critical decisions", 
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "decision_type": {"type": "string", "description": "Type of decision being made"},
                            "options": {"type": "array", "items": {"type": "object"}, "description": "Options to evaluate"},
                            "claude_position": {"type": "object", "description": "Claude's current position"},
                            "evaluation_criteria": {"type": "array", "items": {"type": "string"}},
                            "consensus_threshold": {"type": "number", "default": 0.8}
                        },
                        "required": ["decision_type", "options"]
                    }
                },
                {
                    "name": "devils_advocate",
                    "description": "Gemini challenges proposals to find weaknesses",
                    "inputSchema": {
                        "type": "object", 
                        "properties": {
                            "proposal": {"type": "object", "description": "The proposal to challenge"},
                            "challenge_areas": {
                                "type": "array",
                                "items": {"type": "string", "enum": ["assumptions", "edge_cases", "performance", "security", "maintainability", "scalability"]}
                            },
                            "challenge_intensity": {"type": "string", "enum": ["gentle", "moderate", "aggressive"], "default": "moderate"},
                            "context": {"type": "string", "description": "Additional context"}
                        },
                        "required": ["proposal", "challenge_areas"]
                    }
                }
            ]
        }
    
    async def call_tool(self, tool_name, arguments):
        """Execute tool and return results"""
        task_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()
        
        # Update context
        await self.update_context("ongoing_tasks", {
            "id": task_id,
            "tool": tool_name,
            "started": timestamp
        })
        
        # Log the interaction
        log_entry = {
            "timestamp": timestamp,
            "tool": tool_name,
            "arguments": arguments,
            "task_id": task_id,
            "status": "started"
        }
        await self.log_interaction(task_id, log_entry)
        
        # Special handling for monitor_status
        if tool_name == "monitor_status":
            return await self.get_task_status(arguments.get("task_id", "all"))
        
        # Create task file for Gemini
        task_file = self.dirs['tasks'] / f"{task_id}_{tool_name}.md"
        await self.create_task_file(task_file, tool_name, arguments, task_id)
        
        # Execute Gemini command
        result = await self.execute_gemini(tool_name, task_file, task_id)
        
        # Update context with completion
        await self.update_context("completed_tasks", {
            "id": task_id,
            "tool": tool_name,
            "completed": datetime.now().isoformat(),
            "success": result.get("success", False)
        })
        
        # Log completion
        log_entry["status"] = "completed"
        log_entry["success"] = result.get("success", False)
        log_entry["result_file"] = result.get("findings_file")
        await self.log_interaction(task_id, log_entry)
        
        return result
    
    async def create_task_file(self, task_file, tool_name, arguments, task_id):
        """Create markdown task file for Gemini to process"""
        
        # Read current context
        context = json.loads(self.context_file.read_text())
        
        content = f"""# Task: {tool_name}
**Task ID**: {task_id}
**Timestamp**: {datetime.now().isoformat()}
**Requested by**: Claude Code

## Context
{json.dumps(context.get("project_info", {}), indent=2)}

## Instructions
{await self.format_task_instructions(tool_name, arguments)}

## Expected Output
Please write your findings to: `{self.dirs['findings']}/{task_id}_findings.md`

### Output Format
Structure your response with these sections:
1. **Executive Summary** - Brief overview of findings
2. **Detailed Analysis** - In-depth findings with examples
3. **Recommendations** - Actionable next steps
4. **Code Examples** - If applicable
5. **Metrics** - Any relevant measurements or statistics

### Inter-Agent Communication
- Check `{self.dirs['shared']}` for any relevant context from Claude
- Update `{self.dirs['context']}/agent_context.json` with any important findings
- Flag any items that need Claude's attention with `[CLAUDE-REVIEW]`
"""
        task_file.write_text(content)
    
    async def format_task_instructions(self, tool_name, arguments):
        """Format tool-specific instructions"""
        formatters = {
            "analyze_codebase": lambda args: f"""
Analyze the codebase with the following parameters:

**Query**: {args.get('query')}

**Focus Areas**:
{chr(10).join(f"- {area}" for area in args.get('focus_areas', ['General code quality']))}

**Include Patterns**: {', '.join(args.get('include_patterns', ['*']))}
**Exclude Patterns**: {', '.join(args.get('exclude_patterns', []))}

Please examine:
1. Code patterns and anti-patterns
2. Potential bugs or issues
3. Performance concerns
4. Security implications
5. Suggestions for improvement
""",
            "refactor_code": lambda args: f"""
Refactor code according to these specifications:

**Instructions**: {args.get('instructions')}

**Target Files**:
{chr(10).join(f"- {file}" for file in args.get('files', ['All relevant files']))}

**Patterns to Apply**:
{json.dumps(args.get('patterns', {}), indent=2)}

**Constraints**:
- Preserve tests: {args.get('preserve_tests', True)}
- Maintain backwards compatibility
- Document all changes

Please provide:
1. Summary of changes
2. Before/after code examples
3. Migration guide if needed
4. Test results
""",
            "generate_tests": lambda args: f"""
Generate comprehensive tests for the following:

**Target Files**:
{chr(10).join(f"- {file}" for file in args.get('target_files', []))}

**Test Type**: {args.get('test_type', 'unit')}
**Coverage Target**: {args.get('coverage_target', 80)}%

Requirements:
1. Cover all public methods/functions
2. Include edge cases
3. Test error conditions
4. Provide clear test descriptions
5. Use appropriate mocking/stubbing
""",
            "architecture_review": lambda args: f"""
Review system architecture with focus on:

**Focus Area**: {args.get('focus', 'all')}
**Generate Diagrams**: {args.get('generate_diagrams', True)}
**Suggest Improvements**: {args.get('suggest_improvements', True)}

Please analyze:
1. Current architecture strengths/weaknesses
2. Compliance with best practices
3. Scalability considerations
4. Security architecture
5. Performance bottlenecks
6. Technical debt assessment
""",
            "dependency_audit": lambda args: f"""
Audit project dependencies:

**Checks to perform**:
- Security vulnerabilities: {args.get('check_security', True)}
- License compliance: {args.get('check_licenses', True)}
- Available updates: {args.get('check_updates', True)}
- Generate SBOM: {args.get('generate_sbom', False)}

Please provide:
1. List of all dependencies with versions
2. Security vulnerability report
3. License summary and conflicts
4. Update recommendations
5. Risk assessment
""",
            "rubber_duck_review": lambda args: f"""
## Rubber Duck Debug Session 🦆

**Problem Type**: {args.get('thinking_mode', 'general')}

### The Problem
{args.get('problem_description')}

### What's Been Tried
{chr(10).join(f"{i+1}. {attempt}" for i, attempt in enumerate(args.get('attempted_solutions', ['Nothing yet'])))}

### Code/Context
```
{args.get('code_context', 'No code context provided')}
```

### Specific Questions to Explore
{chr(10).join(f"- {q}" for q in args.get('specific_questions', ['What am I missing?', 'What assumptions am I making?', 'Is there a simpler approach?']))}

---

As your rubber duck, please:

1. **Restate the Problem** - Explain it back in your own words to verify understanding
2. **Question Assumptions** - What implicit assumptions might be causing the block?
3. **Suggest Fresh Perspectives**:
   - Alternative approaches they might not have considered
   - Similar problems and their solutions
   - Simplifications or decompositions
4. **Spot Potential Issues**:
   - Logic errors in attempted solutions
   - Edge cases not considered
   - Performance or scalability concerns
5. **Provide Gentle Hints** - Not full solutions, but nudges in promising directions
6. **Ask Clarifying Questions** - What additional info would help solve this?

Remember: The goal is to help them think through the problem, not just solve it for them.
Act as a patient, insightful colleague who asks good questions.
"""
        }
        
        formatter = formatters.get(tool_name, lambda args: f"Execute {tool_name} with arguments: {json.dumps(args, indent=2)}")
        return formatter(arguments)
    
    async def execute_gemini(self, tool_name, task_file, task_id):
        """Execute Gemini command and capture output"""
        findings_file = self.dirs['findings'] / f"{task_id}_findings.md"
        
        # Note: Adjust this command based on your actual Gemini CLI interface
        # This is a placeholder - replace with actual Gemini command
        cmd = [
            "gemini-code",  # Replace with actual command
            "analyze",
            f"--task-file={task_file}",
            f"--output={findings_file}",
            "--format=markdown"
        ]
        
        # For now, simulate Gemini execution
        # In production, replace this with actual subprocess call
        await asyncio.sleep(2)  # Simulate processing time
        
        # Simulate Gemini output
        findings_content = f"""# Gemini Analysis Results
**Task ID**: {task_id}
**Tool**: {tool_name}
**Completed**: {datetime.now().isoformat()}

## Executive Summary
Analysis completed successfully. Found several items requiring attention.

## Detailed Analysis
Based on the task parameters, here are the findings:

1. **Code Quality**: Overall good with some areas for improvement
2. **Security**: No critical vulnerabilities found
3. **Performance**: Some optimization opportunities identified

## Recommendations
1. Refactor the identified modules
2. Update dependencies to latest stable versions
3. Implement suggested security headers

## Metrics
- Files analyzed: 42
- Issues found: 7 (2 high, 3 medium, 2 low)
- Estimated effort: 16 hours

[CLAUDE-REVIEW] Security findings require your expertise for remediation planning.
"""
        
        findings_file.write_text(findings_content)
        
        return {
            "success": True,
            "task_id": task_id,
            "findings_file": str(findings_file),
            "summary": "Analysis completed successfully. Check findings file for details.",
            "requires_claude_review": "[CLAUDE-REVIEW]" in findings_content
        }
    
    async def get_task_status(self, task_id):
        """Get status of tasks"""
        if task_id == "all":
            # Return all recent tasks
            context = json.loads(self.context_file.read_text())
            return {
                "success": True,
                "ongoing_tasks": context.get("ongoing_tasks", [])[-5:],
                "completed_tasks": context.get("completed_tasks", [])[-5:]
            }
        else:
            # Return specific task
            log_file = self.dirs['logs'] / f"{task_id}_log.json"
            if log_file.exists():
                logs = json.loads(log_file.read_text())
                return {
                    "success": True,
                    "task_id": task_id,
                    "logs": logs
                }
            else:
                return {
                    "success": False,
                    "error": f"Task {task_id} not found"
                }
    
    async def update_context(self, key, value):
        """Update shared context"""
        context = json.loads(self.context_file.read_text())
        
        if key in ["ongoing_tasks", "completed_tasks"]:
            if key not in context:
                context[key] = []
            context[key].append(value)
            # Keep only last 100 items
            context[key] = context[key][-100:]
        else:
            context[key] = value
        
        self.context_file.write_text(json.dumps(context, indent=2))
    
    async def log_interaction(self, task_id, log_entry):
        """Log interactions for monitoring"""
        log_file = self.dirs['logs'] / f"{task_id}_log.json"
        
        logs = []
        if log_file.exists():
            logs = json.loads(log_file.read_text())
        
        logs.append(log_entry)
        log_file.write_text(json.dumps(logs, indent=2))
    
    def handle_completion(self, params):
        """Handle completion requests"""
        # This would provide completions for the MCP protocol
        return {"completions": []}

# MCP Server startup
async def main():
    server = GeminiMCPServer()
    
    # Simple message framing for MCP
    while True:
        try:
            # Read content length header
            header = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not header:
                break
            
            if header.startswith("Content-Length:"):
                length = int(header.split(":")[1].strip())
                
                # Read blank line
                await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                
                # Read content
                content = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.read, length
                )
                
                request = json.loads(content)
                response = await server.handle_request(request)
                
                # Send response with content length header
                response_str = json.dumps(response)
                sys.stdout.write(f"Content-Length: {len(response_str)}\r\n\r\n")
                sys.stdout.write(response_str)
                sys.stdout.flush()
            
        except Exception as e:
            error_response = {
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
            response_str = json.dumps(error_response)
            sys.stdout.write(f"Content-Length: {len(response_str)}\r\n\r\n")
            sys.stdout.write(response_str)
            sys.stdout.flush()

if __name__ == "__main__":
    asyncio.run(main())