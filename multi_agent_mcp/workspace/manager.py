"""
Workspace Manager for coordinating file access between Claude and Gemini.
Provides file locking, change tracking, and conflict resolution.
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
from enum import Enum
import aiofiles
import filelock
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Types of agents in the system."""
    CLAUDE = "claude"
    GEMINI = "gemini"
    HUMAN = "human"


class FileState(Enum):
    """States a file can be in."""
    AVAILABLE = "available"
    LOCKED_READ = "locked_read"
    LOCKED_WRITE = "locked_write"
    MODIFIED = "modified"
    CONFLICT = "conflict"


@dataclass
class FileMetadata:
    """Metadata for tracked files."""
    path: Path
    state: FileState = FileState.AVAILABLE
    locked_by: Optional[AgentType] = None
    last_modified: datetime = field(default_factory=datetime.now)
    checksum: Optional[str] = None
    history: List[Dict[str, Any]] = field(default_factory=list)


class WorkspaceEventHandler(FileSystemEventHandler):
    """Handle file system events in the workspace."""
    
    def __init__(self, workspace_manager):
        self.workspace_manager = workspace_manager
        
    def on_modified(self, event):
        if not event.is_directory:
            asyncio.create_task(
                self.workspace_manager._handle_file_change(Path(event.src_path))
            )
    
    def on_created(self, event):
        if not event.is_directory:
            asyncio.create_task(
                self.workspace_manager._handle_file_created(Path(event.src_path))
            )


class WorkspaceManager:
    """
    Manages shared workspace for multi-agent collaboration.
    
    Features:
    - File locking to prevent conflicts
    - Change tracking and history
    - Automatic conflict detection
    - Agent-specific directories
    - Shared context preservation
    """
    
    def __init__(self, workspace_path: Path):
        """
        Initialize workspace manager.
        
        Args:
            workspace_path: Root workspace directory
        """
        self.workspace_path = Path(workspace_path)
        self.workspace_path.mkdir(exist_ok=True, parents=True)
        
        # Create standard directories
        self.dirs = {
            'shared': self.workspace_path / 'shared',
            'claude': self.workspace_path / 'claude_workspace',
            'gemini': self.workspace_path / 'gemini_workspace',
            'tasks': self.workspace_path / 'tasks',
            'findings': self.workspace_path / 'findings',
            'logs': self.workspace_path / 'logs',
            'context': self.workspace_path / 'context',
            'sandbox': self.workspace_path / 'sandbox',
            'history': self.workspace_path / 'history'
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
        
        # File tracking
        self.file_metadata: Dict[Path, FileMetadata] = {}
        self.lock_dir = self.workspace_path / '.locks'
        self.lock_dir.mkdir(exist_ok=True)
        
        # File system observer
        self.observer = Observer()
        self.event_handler = WorkspaceEventHandler(self)
        
        # Agent activity tracking
        self.agent_activity: Dict[AgentType, Dict[str, Any]] = {
            AgentType.CLAUDE: {'last_active': None, 'current_files': set()},
            AgentType.GEMINI: {'last_active': None, 'current_files': set()},
            AgentType.HUMAN: {'last_active': None, 'current_files': set()}
        }
        
        # Initialize workspace state
        self._initialize_workspace_state()
    
    def _initialize_workspace_state(self):
        """Initialize or restore workspace state."""
        state_file = self.workspace_path / '.workspace_state.json'
        
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    # Restore file metadata
                    for file_data in state.get('files', []):
                        path = Path(file_data['path'])
                        if path.exists():
                            self.file_metadata[path] = FileMetadata(
                                path=path,
                                state=FileState(file_data['state']),
                                locked_by=AgentType(file_data['locked_by']) if file_data.get('locked_by') else None,
                                last_modified=datetime.fromisoformat(file_data['last_modified']),
                                checksum=file_data.get('checksum'),
                                history=file_data.get('history', [])
                            )
            except Exception as e:
                logger.error(f"Error loading workspace state: {e}")
        
        # Start file system monitoring
        self.observer.schedule(
            self.event_handler,
            str(self.workspace_path),
            recursive=True
        )
        self.observer.start()
    
    async def acquire_file(self, 
                          file_path: Path, 
                          agent: AgentType,
                          write: bool = False) -> bool:
        """
        Acquire lock on a file for reading or writing.
        
        Args:
            file_path: Path to file
            agent: Agent requesting lock
            write: Whether write access is needed
        
        Returns:
            True if lock acquired, False otherwise
        """
        abs_path = self.workspace_path / file_path
        lock_path = self.lock_dir / f"{file_path.name}.lock"
        
        # Create file metadata if doesn't exist
        if abs_path not in self.file_metadata:
            self.file_metadata[abs_path] = FileMetadata(path=abs_path)
        
        metadata = self.file_metadata[abs_path]
        
        # Check current state
        if metadata.state == FileState.LOCKED_WRITE and metadata.locked_by != agent:
            logger.warning(f"File {file_path} is locked for writing by {metadata.locked_by}")
            return False
        
        # Try to acquire lock
        lock = filelock.FileLock(lock_path, timeout=5)
        try:
            if write:
                # Exclusive lock for writing
                lock.acquire()
                metadata.state = FileState.LOCKED_WRITE
                metadata.locked_by = agent
            else:
                # Shared lock for reading
                if metadata.state != FileState.LOCKED_WRITE:
                    metadata.state = FileState.LOCKED_READ
                    metadata.locked_by = agent
            
            # Update agent activity
            self.agent_activity[agent]['last_active'] = datetime.now()
            self.agent_activity[agent]['current_files'].add(abs_path)
            
            # Log the acquisition
            await self._log_file_event(abs_path, agent, "acquired", {"write": write})
            
            return True
            
        except filelock.Timeout:
            logger.warning(f"Failed to acquire lock on {file_path} for {agent}")
            return False
    
    async def release_file(self, file_path: Path, agent: AgentType):
        """
        Release lock on a file.
        
        Args:
            file_path: Path to file
            agent: Agent releasing lock
        """
        abs_path = self.workspace_path / file_path
        
        if abs_path in self.file_metadata:
            metadata = self.file_metadata[abs_path]
            if metadata.locked_by == agent:
                metadata.state = FileState.AVAILABLE
                metadata.locked_by = None
                
                # Update agent activity
                self.agent_activity[agent]['current_files'].discard(abs_path)
                
                # Log the release
                await self._log_file_event(abs_path, agent, "released", {})
    
    async def read_file(self, 
                       file_path: Path, 
                       agent: AgentType) -> Optional[str]:
        """
        Read file with proper locking.
        
        Args:
            file_path: Path to file
            agent: Agent reading file
        
        Returns:
            File content or None if failed
        """
        if not await self.acquire_file(file_path, agent, write=False):
            return None
        
        try:
            abs_path = self.workspace_path / file_path
            async with aiofiles.open(abs_path, 'r') as f:
                content = await f.read()
            
            await self._log_file_event(abs_path, agent, "read", {})
            return content
            
        finally:
            await self.release_file(file_path, agent)
    
    async def write_file(self,
                        file_path: Path,
                        content: str,
                        agent: AgentType,
                        backup: bool = True) -> bool:
        """
        Write file with proper locking and backup.
        
        Args:
            file_path: Path to file
            content: Content to write
            agent: Agent writing file
            backup: Whether to create backup
        
        Returns:
            True if successful
        """
        if not await self.acquire_file(file_path, agent, write=True):
            return False
        
        try:
            abs_path = self.workspace_path / file_path
            
            # Create backup if file exists
            if backup and abs_path.exists():
                backup_path = self.dirs['history'] / f"{file_path.name}.{datetime.now().isoformat()}"
                async with aiofiles.open(abs_path, 'r') as src:
                    async with aiofiles.open(backup_path, 'w') as dst:
                        await dst.write(await src.read())
            
            # Write new content
            abs_path.parent.mkdir(exist_ok=True, parents=True)
            async with aiofiles.open(abs_path, 'w') as f:
                await f.write(content)
            
            # Update metadata
            if abs_path in self.file_metadata:
                self.file_metadata[abs_path].last_modified = datetime.now()
                self.file_metadata[abs_path].state = FileState.MODIFIED
            
            await self._log_file_event(abs_path, agent, "wrote", {"size": len(content)})
            return True
            
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            return False
            
        finally:
            await self.release_file(file_path, agent)
    
    async def get_agent_view(self, agent: AgentType) -> Dict[str, Any]:
        """
        Get workspace view for a specific agent.
        
        Args:
            agent: Agent type
        
        Returns:
            Dictionary with agent's view of workspace
        """
        view = {
            'agent': agent.value,
            'workspace_root': str(self.workspace_path),
            'agent_dir': str(self.dirs.get(agent.value, self.dirs['shared'])),
            'shared_files': [],
            'locked_files': [],
            'recent_changes': [],
            'current_context': await self._get_current_context()
        }
        
        # Add file information
        for path, metadata in self.file_metadata.items():
            file_info = {
                'path': str(path.relative_to(self.workspace_path)),
                'state': metadata.state.value,
                'last_modified': metadata.last_modified.isoformat()
            }
            
            if metadata.locked_by == agent:
                view['locked_files'].append(file_info)
            elif metadata.state == FileState.AVAILABLE:
                view['shared_files'].append(file_info)
        
        # Add recent changes
        for event in await self._get_recent_events(agent, limit=10):
            view['recent_changes'].append(event)
        
        return view
    
    async def _handle_file_change(self, file_path: Path):
        """Handle file change event."""
        if file_path in self.file_metadata:
            metadata = self.file_metadata[file_path]
            metadata.last_modified = datetime.now()
            
            # Check for conflicts
            if metadata.state == FileState.LOCKED_WRITE:
                # File was modified while locked - potential conflict
                logger.warning(f"File {file_path} modified while locked by {metadata.locked_by}")
                metadata.state = FileState.CONFLICT
    
    async def _handle_file_created(self, file_path: Path):
        """Handle file creation event."""
        if file_path not in self.file_metadata:
            self.file_metadata[file_path] = FileMetadata(path=file_path)
    
    async def _log_file_event(self, 
                             file_path: Path,
                             agent: AgentType,
                             action: str,
                             details: Dict[str, Any]):
        """Log file event for tracking."""
        event = {
            'timestamp': datetime.now().isoformat(),
            'agent': agent.value,
            'action': action,
            'file': str(file_path.relative_to(self.workspace_path)),
            'details': details
        }
        
        # Add to file history
        if file_path in self.file_metadata:
            self.file_metadata[file_path].history.append(event)
        
        # Log to event file
        log_file = self.dirs['logs'] / f"events_{datetime.now().strftime('%Y%m%d')}.jsonl"
        async with aiofiles.open(log_file, 'a') as f:
            await f.write(json.dumps(event) + '\n')
    
    async def _get_recent_events(self, 
                                agent: AgentType,
                                limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent events for an agent."""
        events = []
        log_files = sorted(self.dirs['logs'].glob("events_*.jsonl"), reverse=True)
        
        for log_file in log_files[:3]:  # Check last 3 days
            async with aiofiles.open(log_file, 'r') as f:
                async for line in f:
                    event = json.loads(line)
                    if event['agent'] == agent.value:
                        events.append(event)
                        if len(events) >= limit:
                            return events
        
        return events
    
    async def _get_current_context(self) -> Dict[str, Any]:
        """Get current shared context."""
        context_file = self.dirs['context'] / 'shared_context.json'
        if context_file.exists():
            async with aiofiles.open(context_file, 'r') as f:
                return json.loads(await f.read())
        return {}
    
    async def save_workspace_state(self):
        """Save current workspace state."""
        state = {
            'timestamp': datetime.now().isoformat(),
            'files': []
        }
        
        for path, metadata in self.file_metadata.items():
            state['files'].append({
                'path': str(path),
                'state': metadata.state.value,
                'locked_by': metadata.locked_by.value if metadata.locked_by else None,
                'last_modified': metadata.last_modified.isoformat(),
                'checksum': metadata.checksum,
                'history': metadata.history[-10:]  # Keep last 10 events
            })
        
        state_file = self.workspace_path / '.workspace_state.json'
        async with aiofiles.open(state_file, 'w') as f:
            await f.write(json.dumps(state, indent=2))
    
    def cleanup(self):
        """Clean up resources."""
        self.observer.stop()
        self.observer.join()