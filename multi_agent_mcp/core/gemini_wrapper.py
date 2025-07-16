"""
Gemini Code Assist wrapper for native integration with Claude Code.
Handles command execution, sandbox mode, and response parsing.
"""
import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import aiofiles
import logging

logger = logging.getLogger(__name__)


class GeminiMode(Enum):
    """Gemini execution modes."""
    NORMAL = "normal"
    SANDBOX = "sandbox"
    REVIEW = "review"
    GENERATE = "generate"


@dataclass
class GeminiResponse:
    """Structured response from Gemini."""
    success: bool
    content: str
    metadata: Dict[str, Any]
    sandbox_artifacts: Optional[List[Path]] = None
    execution_time: float = 0.0


class GeminiWrapper:
    """
    Wrapper for Gemini Code Assist CLI with enhanced features for multi-agent collaboration.
    """
    
    def __init__(self, 
                 command: str = None,
                 workspace_path: Optional[Path] = None,
                 enable_sandbox: bool = True,
                 timeout: int = 300):
        """
        Initialize Gemini wrapper.
        
        Args:
            command: Gemini CLI command name/path
            workspace_path: Shared workspace path
            enable_sandbox: Enable sandbox mode for safe code execution
            timeout: Command timeout in seconds
        """
        # Auto-detect Gemini command or use environment variable
        self.command = command or os.environ.get("GEMINI_COMMAND") or self._detect_gemini_command()
        self.workspace_path = workspace_path or Path("./agent_workspace")
        self.enable_sandbox = enable_sandbox
        self.timeout = timeout
        self.sandbox_dir = self.workspace_path / "sandbox"
        self.sandbox_dir.mkdir(exist_ok=True, parents=True)
        
        # Verify Gemini is available
        self._verify_gemini()
    
    def _detect_gemini_command(self) -> str:
        """Auto-detect available Gemini command."""
        possible_commands = ["gemini", "gemini-code-assist", "gemini-cli", "aistudio"]
        
        for cmd in possible_commands:
            try:
                result = subprocess.run(
                    [cmd, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    logger.info(f"Auto-detected Gemini command: {cmd}")
                    return cmd
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        # Fallback to default
        return "gemini"
    
    def _verify_gemini(self):
        """Verify Gemini CLI is available."""
        try:
            result = subprocess.run(
                [self.command, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError(f"Gemini CLI not found or returned error: {result.stderr}")
            logger.info(f"Gemini CLI verified: {result.stdout.strip()}")
        except FileNotFoundError:
            raise RuntimeError(f"Gemini CLI '{self.command}' not found in PATH")
        except subprocess.TimeoutExpired:
            raise RuntimeError("Gemini CLI verification timed out")
    
    async def analyze_code(self, 
                          code_path: Path,
                          query: str,
                          focus_areas: List[str] = None,
                          include_patterns: List[str] = None,
                          exclude_patterns: List[str] = None,
                          mode: GeminiMode = GeminiMode.NORMAL) -> GeminiResponse:
        """
        Analyze code using Gemini.
        
        Args:
            code_path: Path to code directory or file
            query: Analysis query
            focus_areas: Specific areas to focus on
            include_patterns: File patterns to include
            exclude_patterns: File patterns to exclude
            mode: Execution mode
        
        Returns:
            GeminiResponse with analysis results
        """
        # Build command
        cmd = [self.command, "analyze", str(code_path)]
        cmd.extend(["--query", query])
        
        if focus_areas:
            cmd.extend(["--focus", ",".join(focus_areas)])
        
        if include_patterns:
            cmd.extend(["--include", ",".join(include_patterns)])
            
        if exclude_patterns:
            cmd.extend(["--exclude", ",".join(exclude_patterns)])
        
        if mode == GeminiMode.SANDBOX and self.enable_sandbox:
            cmd.extend(["--sandbox", str(self.sandbox_dir)])
        
        # Add output format
        cmd.extend(["--format", "json"])
        
        return await self._execute_command(cmd, mode)
    
    async def refactor_code(self,
                           files: List[Path],
                           instructions: str,
                           preserve_tests: bool = True,
                           dry_run: bool = False) -> GeminiResponse:
        """
        Refactor code files according to instructions.
        
        Args:
            files: List of files to refactor
            instructions: Refactoring instructions
            preserve_tests: Ensure tests still pass
            dry_run: Preview changes without applying
        
        Returns:
            GeminiResponse with refactoring results
        """
        cmd = [self.command, "refactor"]
        cmd.extend([str(f) for f in files])
        cmd.extend(["--instructions", instructions])
        
        if preserve_tests:
            cmd.append("--preserve-tests")
        
        if dry_run:
            cmd.append("--dry-run")
        
        cmd.extend(["--format", "json"])
        
        return await self._execute_command(cmd, GeminiMode.NORMAL)
    
    async def generate_tests(self,
                            target_files: List[Path],
                            test_type: str = "unit",
                            coverage_target: int = 80,
                            test_framework: Optional[str] = None) -> GeminiResponse:
        """
        Generate tests for target files.
        
        Args:
            target_files: Files to generate tests for
            test_type: Type of tests (unit, integration, e2e)
            coverage_target: Target coverage percentage
            test_framework: Specific test framework to use
        
        Returns:
            GeminiResponse with generated tests
        """
        cmd = [self.command, "generate-tests"]
        cmd.extend([str(f) for f in target_files])
        cmd.extend(["--type", test_type])
        cmd.extend(["--coverage", str(coverage_target)])
        
        if test_framework:
            cmd.extend(["--framework", test_framework])
        
        cmd.extend(["--format", "json"])
        
        return await self._execute_command(cmd, GeminiMode.GENERATE)
    
    async def review_code(self,
                         files: List[Path],
                         review_type: str = "comprehensive",
                         security_check: bool = True,
                         performance_check: bool = True) -> GeminiResponse:
        """
        Perform code review.
        
        Args:
            files: Files to review
            review_type: Type of review
            security_check: Include security analysis
            performance_check: Include performance analysis
        
        Returns:
            GeminiResponse with review results
        """
        cmd = [self.command, "review"]
        cmd.extend([str(f) for f in files])
        cmd.extend(["--type", review_type])
        
        if security_check:
            cmd.append("--security")
        
        if performance_check:
            cmd.append("--performance")
        
        cmd.extend(["--format", "json"])
        
        return await self._execute_command(cmd, GeminiMode.REVIEW)
    
    async def execute_in_sandbox(self,
                                code: str,
                                language: str = "python",
                                timeout: int = 60) -> GeminiResponse:
        """
        Execute code in Gemini's sandbox environment.
        
        Args:
            code: Code to execute
            language: Programming language
            timeout: Execution timeout
        
        Returns:
            GeminiResponse with execution results
        """
        if not self.enable_sandbox:
            raise RuntimeError("Sandbox mode is disabled")
        
        # Write code to temporary file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=f'.{language}',
            dir=self.sandbox_dir,
            delete=False
        ) as f:
            f.write(code)
            code_file = Path(f.name)
        
        try:
            cmd = [
                self.command, "sandbox-execute",
                str(code_file),
                "--language", language,
                "--timeout", str(timeout),
                "--format", "json"
            ]
            
            response = await self._execute_command(cmd, GeminiMode.SANDBOX)
            
            # Collect sandbox artifacts
            artifacts = list(self.sandbox_dir.glob("*"))
            response.sandbox_artifacts = [a for a in artifacts if a != code_file]
            
            return response
        finally:
            # Cleanup
            code_file.unlink(missing_ok=True)
    
    async def _execute_command(self, 
                              cmd: List[str], 
                              mode: GeminiMode) -> GeminiResponse:
        """
        Execute Gemini command and parse response.
        
        Args:
            cmd: Command to execute
            mode: Execution mode
        
        Returns:
            GeminiResponse
        """
        logger.info(f"Executing Gemini command: {' '.join(cmd)}")
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Run command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace_path)
            )
            
            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.terminate()
                await process.wait()
                raise TimeoutError(f"Gemini command timed out after {self.timeout}s")
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            # Parse response
            if process.returncode == 0:
                try:
                    # Try to parse as JSON
                    result = json.loads(stdout.decode())
                    return GeminiResponse(
                        success=True,
                        content=result.get("content", ""),
                        metadata=result.get("metadata", {}),
                        execution_time=execution_time
                    )
                except json.JSONDecodeError:
                    # Fallback to plain text
                    return GeminiResponse(
                        success=True,
                        content=stdout.decode(),
                        metadata={"mode": mode.value},
                        execution_time=execution_time
                    )
            else:
                error_msg = stderr.decode() or stdout.decode()
                logger.error(f"Gemini command failed: {error_msg}")
                return GeminiResponse(
                    success=False,
                    content=error_msg,
                    metadata={"mode": mode.value, "return_code": process.returncode},
                    execution_time=execution_time
                )
                
        except Exception as e:
            logger.exception("Error executing Gemini command")
            return GeminiResponse(
                success=False,
                content=str(e),
                metadata={"mode": mode.value, "error_type": type(e).__name__},
                execution_time=asyncio.get_event_loop().time() - start_time
            )
    
    async def chat_with_context(self, 
                               message: str,
                               context_files: List[Path] = None,
                               previous_messages: List[Dict[str, str]] = None) -> GeminiResponse:
        """
        Interactive chat with Gemini, maintaining context.
        
        Args:
            message: User message
            context_files: Files to include as context
            previous_messages: Previous conversation history
        
        Returns:
            GeminiResponse with Gemini's reply
        """
        cmd = [self.command, "chat", "--message", message]
        
        if context_files:
            for f in context_files:
                cmd.extend(["--context", str(f)])
        
        if previous_messages:
            # Save conversation history to temp file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.json',
                delete=False
            ) as f:
                json.dump(previous_messages, f)
                history_file = f.name
            
            cmd.extend(["--history", history_file])
        
        cmd.extend(["--format", "json"])
        
        try:
            response = await self._execute_command(cmd, GeminiMode.NORMAL)
            return response
        finally:
            if previous_messages and 'history_file' in locals():
                Path(history_file).unlink(missing_ok=True)