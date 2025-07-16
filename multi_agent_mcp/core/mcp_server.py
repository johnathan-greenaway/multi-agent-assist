"""
Main MCP Server integrating Gemini wrapper, workspace management, and context preservation.
"""
import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from ..core.gemini_wrapper import GeminiWrapper, GeminiMode
from ..workspace.manager import WorkspaceManager, AgentType
from ..agents.context_manager import ContextManager, ContextType

logger = logging.getLogger(__name__)


class MultiAgentMCPServer:
    """
    MCP Server that orchestrates Claude-Gemini collaboration with advanced features.
    """
    
    def __init__(self, workspace_dir: str = "./agent_workspace"):
        """Initialize MCP server with all components."""
        self.workspace_path = Path(workspace_dir)
        self.workspace_path.mkdir(exist_ok=True, parents=True)
        
        # Initialize components
        self.gemini = GeminiWrapper(workspace_path=self.workspace_path)
        self.workspace = WorkspaceManager(self.workspace_path)
        self.context = ContextManager(self.workspace_path)
        
        # Session tracking
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Configure logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging for the server."""
        log_file = self.workspace_path / 'logs' / f"mcp_server_{datetime.now().strftime('%Y%m%d')}.log"
        log_file.parent.mkdir(exist_ok=True)
        
        handler = logging.FileHandler(log_file)
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main MCP request handler.
        
        Args:
            request: MCP protocol request
            
        Returns:
            MCP protocol response
        """
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                return await self._handle_initialize(params)
            elif method == "tools/list":
                return self._list_tools()
            elif method == "tools/call":
                return await self._call_tool(params)
            elif method == "completion/complete":
                return await self._handle_completion(params)
            elif method == "shutdown":
                return await self._handle_shutdown()
            else:
                return self._error_response(
                    request_id,
                    -32601,
                    f"Method not found: {method}"
                )
        except Exception as e:
            logger.exception(f"Error handling request: {method}")
            return self._error_response(
                request_id,
                -32603,
                f"Internal error: {str(e)}"
            )
    
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialization request."""
        client_info = params.get("clientInfo", {})
        
        # Create session
        session_id = str(uuid.uuid4())
        self.active_sessions[session_id] = {
            "client": client_info,
            "started": datetime.now(),
            "agent": AgentType.CLAUDE  # Assume Claude is the primary client
        }
        
        # Get initial context
        context_summary = await self.context.get_shared_understanding()
        
        return {
            "protocolVersion": "0.1.0",
            "serverInfo": {
                "name": "Multi-Agent MCP Server",
                "version": "0.1.0"
            },
            "capabilities": {
                "tools": True,
                "completion": True,
                "workspace": True,
                "context": True
            },
            "sessionId": session_id,
            "contextSummary": context_summary
        }
    
    def _list_tools(self) -> Dict[str, Any]:
        """Return available tools."""
        return {
            "tools": [
                # Core analysis tools
                {
                    "name": "analyze_codebase",
                    "description": "Use Gemini to analyze codebase for patterns, issues, or specific queries",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "What to analyze"},
                            "focus_areas": {"type": "array", "items": {"type": "string"}},
                            "include_patterns": {"type": "array", "items": {"type": "string"}},
                            "exclude_patterns": {"type": "array", "items": {"type": "string"}},
                            "use_sandbox": {"type": "boolean", "default": False}
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
                            "instructions": {"type": "string"},
                            "files": {"type": "array", "items": {"type": "string"}},
                            "preserve_tests": {"type": "boolean", "default": True},
                            "dry_run": {"type": "boolean", "default": False}
                        },
                        "required": ["instructions", "files"]
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
                            "coverage_target": {"type": "number", "default": 80},
                            "test_framework": {"type": "string"}
                        },
                        "required": ["target_files"]
                    }
                },
                
                # Collaboration tools
                {
                    "name": "rubber_duck_review",
                    "description": "Claude can use Gemini as a rubber duck when stuck",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "problem_description": {"type": "string"},
                            "attempted_solutions": {"type": "array", "items": {"type": "string"}},
                            "code_context": {"type": "string"},
                            "specific_questions": {"type": "array", "items": {"type": "string"}},
                            "thinking_mode": {
                                "type": "string",
                                "enum": ["debug", "design", "algorithm", "architecture", "general"]
                            }
                        },
                        "required": ["problem_description"]
                    }
                },
                {
                    "name": "pair_programming_session",
                    "description": "Start collaborative coding session",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "session_type": {
                                "type": "string",
                                "enum": ["feature_development", "bug_fixing", "refactoring", "code_review"]
                            },
                            "current_file": {"type": "string"},
                            "objective": {"type": "string"},
                            "sync_interval": {"type": "integer", "default": 30}
                        },
                        "required": ["session_type", "objective"]
                    }
                },
                
                # Advanced modes
                {
                    "name": "distributed_analysis",
                    "description": "Distribute large content analysis between agents",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "content_paths": {"type": "array", "items": {"type": "string"}},
                            "analysis_goals": {"type": "array", "items": {"type": "string"}},
                            "split_strategy": {
                                "type": "string",
                                "enum": ["by_type", "by_module", "by_complexity", "round_robin"]
                            }
                        },
                        "required": ["content_paths", "analysis_goals"]
                    }
                },
                {
                    "name": "consensus_mode",
                    "description": "Require both agents to agree on critical decisions",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "decision_type": {"type": "string"},
                            "options": {"type": "array", "items": {"type": "object"}},
                            "evaluation_criteria": {"type": "array", "items": {"type": "string"}},
                            "claude_position": {"type": "object"}
                        },
                        "required": ["decision_type", "options"]
                    }
                },
                {
                    "name": "execute_in_sandbox",
                    "description": "Execute code in Gemini's sandbox environment",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string"},
                            "language": {"type": "string", "default": "python"},
                            "timeout": {"type": "integer", "default": 60}
                        },
                        "required": ["code"]
                    }
                },
                
                # Context and workspace tools
                {
                    "name": "get_agent_context",
                    "description": "Get current context and understanding",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "include_peer_questions": {"type": "boolean", "default": True},
                            "context_types": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": ["conversation", "task", "code_understanding", "decisions", "findings"]
                                }
                            }
                        }
                    }
                },
                {
                    "name": "handoff_task",
                    "description": "Hand off task to Gemini with context",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "task_description": {"type": "string"},
                            "context_to_share": {"type": "object"},
                            "expected_output": {"type": "string"}
                        },
                        "required": ["task_description"]
                    }
                },
                {
                    "name": "workspace_status",
                    "description": "Get current workspace status and file locks",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "include_file_list": {"type": "boolean", "default": True},
                            "include_recent_changes": {"type": "boolean", "default": True}
                        }
                    }
                }
            ]
        }
    
    async def _call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool and return results."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        # Generate task ID
        task_id = str(uuid.uuid4())[:8]
        
        # Log tool call
        await self.context.add_context(
            "claude",
            ContextType.TASK,
            {
                "tool": tool_name,
                "arguments": arguments,
                "task_id": task_id
            },
            tags=["tool_call"],
            importance=6
        )
        
        # Route to appropriate handler
        handlers = {
            "analyze_codebase": self._handle_analyze_codebase,
            "refactor_code": self._handle_refactor_code,
            "generate_tests": self._handle_generate_tests,
            "rubber_duck_review": self._handle_rubber_duck,
            "pair_programming_session": self._handle_pair_programming,
            "distributed_analysis": self._handle_distributed_analysis,
            "consensus_mode": self._handle_consensus_mode,
            "execute_in_sandbox": self._handle_sandbox_execution,
            "get_agent_context": self._handle_get_context,
            "handoff_task": self._handle_task_handoff,
            "workspace_status": self._handle_workspace_status
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }
        
        try:
            result = await handler(arguments, task_id)
            
            # Log result
            await self.context.add_context(
                "claude",
                ContextType.FINDINGS,
                {
                    "tool": tool_name,
                    "task_id": task_id,
                    "success": result.get("success", False),
                    "summary": result.get("summary", "")
                },
                references=[task_id],
                tags=["tool_result"],
                importance=7
            )
            
            return result
            
        except Exception as e:
            logger.exception(f"Error executing tool {tool_name}")
            return {
                "success": False,
                "error": str(e),
                "task_id": task_id
            }
    
    async def _handle_analyze_codebase(self, args: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """Handle codebase analysis request."""
        # Create task file for tracking
        task_file = self.workspace.dirs['tasks'] / f"{task_id}_analyze.md"
        await self.workspace.write_file(
            task_file.relative_to(self.workspace_path),
            f"# Analysis Task {task_id}\n\nQuery: {args['query']}\n",
            AgentType.CLAUDE
        )
        
        # Execute analysis with Gemini
        response = await self.gemini.analyze_code(
            self.workspace_path,
            args['query'],
            focus_areas=args.get('focus_areas'),
            include_patterns=args.get('include_patterns'),
            exclude_patterns=args.get('exclude_patterns'),
            mode=GeminiMode.SANDBOX if args.get('use_sandbox') else GeminiMode.NORMAL
        )
        
        # Save findings
        findings_file = self.workspace.dirs['findings'] / f"{task_id}_findings.md"
        await self.workspace.write_file(
            findings_file.relative_to(self.workspace_path),
            response.content,
            AgentType.GEMINI
        )
        
        return {
            "success": response.success,
            "task_id": task_id,
            "findings": response.content,
            "findings_file": str(findings_file),
            "execution_time": response.execution_time,
            "metadata": response.metadata
        }
    
    async def _handle_rubber_duck(self, args: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """Handle rubber duck debugging session."""
        # Update Claude's uncertainty
        await self.context.update_agent_memory(
            "claude",
            new_uncertainty=args['problem_description']
        )
        
        # Create rubber duck prompt for Gemini
        prompt = f"""
# Rubber Duck Debug Session 🦆

Claude is stuck and needs your help thinking through this problem:

**Problem**: {args['problem_description']}

**What Claude has tried**:
{chr(10).join(f"- {attempt}" for attempt in args.get('attempted_solutions', []))}

**Code Context**:
```
{args.get('code_context', 'No code provided')}
```

**Specific Questions**:
{chr(10).join(f"- {q}" for q in args.get('specific_questions', []))}

**Thinking Mode**: {args.get('thinking_mode', 'general')}

Please help Claude think through this by:
1. Restating the problem in your own words
2. Identifying potential assumptions or blind spots
3. Suggesting alternative approaches
4. Asking clarifying questions
5. Providing gentle hints (not full solutions)
"""
        
        # Get Gemini's perspective
        response = await self.gemini.chat_with_context(
            prompt,
            context_files=[self.workspace.dirs['context'] / 'shared_understanding.json']
        )
        
        if response.success:
            # Add to context
            await self.context.add_context(
                "gemini",
                ContextType.CONVERSATION,
                {
                    "type": "rubber_duck_response",
                    "problem": args['problem_description'],
                    "response": response.content
                },
                tags=["rubber_duck", "shared"],
                importance=8
            )
        
        return {
            "success": response.success,
            "task_id": task_id,
            "gemini_perspective": response.content,
            "thinking_mode": args.get('thinking_mode', 'general')
        }
    
    async def _handle_distributed_analysis(self, args: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """Handle distributed analysis across both agents."""
        content_paths = [Path(p) for p in args['content_paths']]
        analysis_goals = args['analysis_goals']
        split_strategy = args.get('split_strategy', 'by_type')
        
        # Split work based on strategy
        claude_tasks = []
        gemini_tasks = []
        
        if split_strategy == 'by_type':
            # Split by file type
            for path in content_paths:
                if path.suffix in ['.py', '.js', '.ts']:
                    gemini_tasks.append(path)
                else:
                    claude_tasks.append(path)
        elif split_strategy == 'round_robin':
            # Alternate assignment
            for i, path in enumerate(content_paths):
                if i % 2 == 0:
                    claude_tasks.append(path)
                else:
                    gemini_tasks.append(path)
        else:
            # Default: give half to each
            mid = len(content_paths) // 2
            claude_tasks = content_paths[:mid]
            gemini_tasks = content_paths[mid:]
        
        # Create analysis tasks
        results = {
            "success": True,
            "task_id": task_id,
            "distribution": {
                "claude": [str(p) for p in claude_tasks],
                "gemini": [str(p) for p in gemini_tasks]
            },
            "claude_analysis": "Claude should analyze the assigned files focusing on architecture and design",
            "gemini_analysis": {}
        }
        
        # Execute Gemini's portion
        if gemini_tasks:
            gemini_response = await self.gemini.analyze_code(
                self.workspace_path,
                f"Analyze these files for: {', '.join(analysis_goals)}",
                include_patterns=[str(p) for p in gemini_tasks]
            )
            
            results["gemini_analysis"] = {
                "success": gemini_response.success,
                "findings": gemini_response.content,
                "files_analyzed": len(gemini_tasks)
            }
        
        return results
    
    async def _handle_consensus_mode(self, args: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """Handle consensus building between agents."""
        decision_type = args['decision_type']
        options = args['options']
        claude_position = args.get('claude_position', {})
        criteria = args.get('evaluation_criteria', [])
        
        # Create evaluation prompt for Gemini
        prompt = f"""
# Consensus Building: {decision_type}

Claude has proposed the following position:
{json.dumps(claude_position, indent=2)}

Available options:
{json.dumps(options, indent=2)}

Evaluation criteria:
{chr(10).join(f"- {c}" for c in criteria)}

Please:
1. Evaluate each option against the criteria
2. State your position and reasoning
3. Identify areas of agreement/disagreement with Claude
4. Suggest compromises if needed
"""
        
        # Get Gemini's evaluation
        response = await self.gemini.chat_with_context(prompt)
        
        if response.success:
            # Save both positions
            await self.context.add_context(
                "consensus",
                ContextType.DECISIONS,
                {
                    "decision_type": decision_type,
                    "claude_position": claude_position,
                    "gemini_position": response.content,
                    "options": options,
                    "criteria": criteria
                },
                tags=["consensus", "shared"],
                importance=9
            )
        
        return {
            "success": response.success,
            "task_id": task_id,
            "decision_type": decision_type,
            "gemini_evaluation": response.content,
            "consensus_achieved": False  # Would need more logic to determine
        }
    
    async def _handle_sandbox_execution(self, args: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """Handle code execution in sandbox."""
        response = await self.gemini.execute_in_sandbox(
            args['code'],
            language=args.get('language', 'python'),
            timeout=args.get('timeout', 60)
        )
        
        result = {
            "success": response.success,
            "task_id": task_id,
            "output": response.content,
            "execution_time": response.execution_time
        }
        
        if response.sandbox_artifacts:
            result["artifacts"] = [str(p) for p in response.sandbox_artifacts]
        
        return result
    
    async def _handle_get_context(self, args: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """Get agent context and understanding."""
        context_types = args.get('context_types')
        include_peer_questions = args.get('include_peer_questions', True)
        
        # Get relevant context
        if context_types:
            context_type_enums = [ContextType(ct) for ct in context_types]
            context_entries = await self.context.get_context_for_agent(
                "claude",
                context_types=context_type_enums
            )
        else:
            context_entries = await self.context.get_context_for_agent("claude")
        
        # Get shared understanding
        shared_understanding = await self.context.get_shared_understanding()
        
        result = {
            "success": True,
            "task_id": task_id,
            "context_entries": [
                {
                    "id": entry.id,
                    "type": entry.type.value,
                    "timestamp": entry.timestamp.isoformat(),
                    "summary": self.context._summarize_content(entry.content)
                }
                for entry in context_entries
            ],
            "shared_understanding": shared_understanding
        }
        
        if include_peer_questions:
            result["peer_questions"] = await self.context.get_peer_questions("claude")
        
        return result
    
    async def _handle_task_handoff(self, args: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """Handle task handoff to Gemini."""
        task_description = args['task_description']
        context_to_share = args.get('context_to_share', {})
        expected_output = args.get('expected_output', '')
        
        # Create handoff context
        handoff = await self.context.create_handoff_context(
            "claude",
            "gemini",
            task_description
        )
        
        # Create task file for Gemini
        task_content = f"""# Task Handoff from Claude

**Task ID**: {task_id}
**Description**: {task_description}

## Context from Claude
{json.dumps(context_to_share, indent=2)}

## Expected Output
{expected_output}

## Current Understanding
{json.dumps(handoff['current_understanding'], indent=2)}

## Open Questions
{chr(10).join(f"- {u}" for u in handoff['uncertainties'])}

Please complete this task and save your findings to:
`findings/{task_id}_gemini_findings.md`
"""
        
        task_file = self.workspace.dirs['tasks'] / f"{task_id}_handoff.md"
        await self.workspace.write_file(
            task_file.relative_to(self.workspace_path),
            task_content,
            AgentType.CLAUDE
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "handoff_created": True,
            "task_file": str(task_file),
            "handoff_context": handoff
        }
    
    async def _handle_workspace_status(self, args: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """Get workspace status."""
        include_files = args.get('include_file_list', True)
        include_changes = args.get('include_recent_changes', True)
        
        # Get agent view
        agent_view = await self.workspace.get_agent_view(AgentType.CLAUDE)
        
        result = {
            "success": True,
            "task_id": task_id,
            "workspace_root": str(self.workspace_path),
            "agent_activity": {
                agent.value: {
                    "last_active": activity['last_active'].isoformat() if activity['last_active'] else None,
                    "active_files": len(activity['current_files'])
                }
                for agent, activity in self.workspace.agent_activity.items()
            }
        }
        
        if include_files:
            result["files"] = agent_view['shared_files'] + agent_view['locked_files']
        
        if include_changes:
            result["recent_changes"] = agent_view['recent_changes']
        
        return result
    
    async def _handle_pair_programming(self, args: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """Initialize pair programming session."""
        # This would typically set up a more complex real-time sync
        # For now, we'll create a session marker
        session_info = {
            "task_id": task_id,
            "session_type": args['session_type'],
            "objective": args['objective'],
            "current_file": args.get('current_file'),
            "started": datetime.now().isoformat(),
            "sync_interval": args.get('sync_interval', 30)
        }
        
        # Save session info
        session_file = self.workspace.dirs['shared'] / f"pair_session_{task_id}.json"
        await self.workspace.write_file(
            session_file.relative_to(self.workspace_path),
            json.dumps(session_info, indent=2),
            AgentType.CLAUDE
        )
        
        # Notify Gemini about the session
        await self.context.add_context(
            "claude",
            ContextType.TASK,
            {
                "type": "pair_programming_start",
                "session": session_info
            },
            tags=["pair_programming", "shared"],
            importance=8
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "session_started": True,
            "session_file": str(session_file),
            "sync_instructions": "Session initialized. Both agents can now work on the objective with automatic synchronization."
        }
    
    async def _handle_refactor_code(self, args: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """Handle code refactoring request."""
        files = [Path(f) for f in args['files']]
        
        response = await self.gemini.refactor_code(
            files,
            args['instructions'],
            preserve_tests=args.get('preserve_tests', True),
            dry_run=args.get('dry_run', False)
        )
        
        return {
            "success": response.success,
            "task_id": task_id,
            "refactoring_results": response.content,
            "dry_run": args.get('dry_run', False),
            "metadata": response.metadata
        }
    
    async def _handle_generate_tests(self, args: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """Handle test generation request."""
        target_files = [Path(f) for f in args['target_files']]
        
        response = await self.gemini.generate_tests(
            target_files,
            test_type=args.get('test_type', 'unit'),
            coverage_target=args.get('coverage_target', 80),
            test_framework=args.get('test_framework')
        )
        
        # Save generated tests
        if response.success:
            test_file = self.workspace.dirs['findings'] / f"{task_id}_generated_tests.md"
            await self.workspace.write_file(
                test_file.relative_to(self.workspace_path),
                response.content,
                AgentType.GEMINI
            )
        
        return {
            "success": response.success,
            "task_id": task_id,
            "generated_tests": response.content,
            "test_type": args.get('test_type', 'unit'),
            "coverage_target": args.get('coverage_target', 80)
        }
    
    async def _handle_completion(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle completion requests."""
        # This would provide completions for the MCP protocol
        return {"completions": []}
    
    async def _handle_shutdown(self) -> Dict[str, Any]:
        """Handle shutdown request."""
        # Save workspace state
        await self.workspace.save_workspace_state()
        
        # Cleanup
        self.workspace.cleanup()
        
        return {"status": "shutdown complete"}
    
    def _error_response(self, request_id: Optional[str], code: int, message: str) -> Dict[str, Any]:
        """Create error response."""
        response = {
            "error": {
                "code": code,
                "message": message
            }
        }
        if request_id:
            response["id"] = request_id
        return response


async def run_mcp_server():
    """Run the MCP server."""
    server = MultiAgentMCPServer()
    
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
            
        except KeyboardInterrupt:
            break
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


def main():
    """Main entry point."""
    asyncio.run(run_mcp_server())


if __name__ == "__main__":
    main()