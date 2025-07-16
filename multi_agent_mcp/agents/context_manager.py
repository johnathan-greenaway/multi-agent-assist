"""
Context Manager for preserving and sharing context between Claude and Gemini.
Handles conversation history, task state, and agent memory.
"""
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
import aiofiles
import logging

logger = logging.getLogger(__name__)


class ContextType(Enum):
    """Types of context that can be shared."""
    CONVERSATION = "conversation"
    TASK = "task"
    CODE_UNDERSTANDING = "code_understanding"
    DECISIONS = "decisions"
    FINDINGS = "findings"
    QUESTIONS = "questions"


@dataclass
class ContextEntry:
    """Single context entry."""
    id: str
    type: ContextType
    agent: str
    timestamp: datetime
    content: Dict[str, Any]
    references: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    importance: int = 5  # 1-10 scale


@dataclass
class AgentMemory:
    """Agent's working memory."""
    agent_name: str
    current_task: Optional[str] = None
    understanding: Dict[str, Any] = field(default_factory=dict)
    uncertainties: List[str] = field(default_factory=list)
    decisions_made: List[Dict[str, Any]] = field(default_factory=list)
    questions_for_peer: List[str] = field(default_factory=list)


class ContextManager:
    """
    Manages shared context between Claude and Gemini.
    
    Features:
    - Persistent context storage
    - Context summarization for efficiency
    - Importance-based retention
    - Cross-agent question/answer tracking
    - Task continuity across sessions
    """
    
    def __init__(self, workspace_path: Path, max_context_size: int = 50000):
        """
        Initialize context manager.
        
        Args:
            workspace_path: Root workspace directory
            max_context_size: Maximum context size in tokens (approximate)
        """
        self.workspace_path = Path(workspace_path)
        self.context_dir = self.workspace_path / 'context'
        self.context_dir.mkdir(exist_ok=True, parents=True)
        
        self.max_context_size = max_context_size
        self.context_entries: List[ContextEntry] = []
        self.agent_memories: Dict[str, AgentMemory] = {}
        
        # Context files
        self.files = {
            'current': self.context_dir / 'current_context.json',
            'claude_memory': self.context_dir / 'claude_memory.json',
            'gemini_memory': self.context_dir / 'gemini_memory.json',
            'shared_understanding': self.context_dir / 'shared_understanding.json',
            'conversation_history': self.context_dir / 'conversation_history.jsonl'
        }
        
        # Initialize memories
        self.agent_memories['claude'] = AgentMemory('claude')
        self.agent_memories['gemini'] = AgentMemory('gemini')
        
        # Load existing context
        asyncio.create_task(self._load_context())
    
    async def _load_context(self):
        """Load existing context from files."""
        # Load current context
        if self.files['current'].exists():
            try:
                async with aiofiles.open(self.files['current'], 'r') as f:
                    data = json.loads(await f.read())
                    for entry_data in data.get('entries', []):
                        entry = ContextEntry(
                            id=entry_data['id'],
                            type=ContextType(entry_data['type']),
                            agent=entry_data['agent'],
                            timestamp=datetime.fromisoformat(entry_data['timestamp']),
                            content=entry_data['content'],
                            references=entry_data.get('references', []),
                            tags=entry_data.get('tags', []),
                            importance=entry_data.get('importance', 5)
                        )
                        self.context_entries.append(entry)
            except Exception as e:
                logger.error(f"Error loading context: {e}")
        
        # Load agent memories
        for agent_name, memory_file in [
            ('claude', self.files['claude_memory']),
            ('gemini', self.files['gemini_memory'])
        ]:
            if memory_file.exists():
                try:
                    async with aiofiles.open(memory_file, 'r') as f:
                        data = json.loads(await f.read())
                        memory = AgentMemory(
                            agent_name=agent_name,
                            current_task=data.get('current_task'),
                            understanding=data.get('understanding', {}),
                            uncertainties=data.get('uncertainties', []),
                            decisions_made=data.get('decisions_made', []),
                            questions_for_peer=data.get('questions_for_peer', [])
                        )
                        self.agent_memories[agent_name] = memory
                except Exception as e:
                    logger.error(f"Error loading {agent_name} memory: {e}")
    
    async def add_context(self,
                         agent: str,
                         context_type: ContextType,
                         content: Dict[str, Any],
                         references: List[str] = None,
                         tags: List[str] = None,
                         importance: int = 5) -> str:
        """
        Add context entry.
        
        Args:
            agent: Agent adding context
            context_type: Type of context
            content: Context content
            references: Related context IDs
            tags: Tags for categorization
            importance: Importance level (1-10)
        
        Returns:
            Context entry ID
        """
        entry_id = f"{agent}_{context_type.value}_{datetime.now().timestamp()}"
        
        entry = ContextEntry(
            id=entry_id,
            type=context_type,
            agent=agent,
            timestamp=datetime.now(),
            content=content,
            references=references or [],
            tags=tags or [],
            importance=importance
        )
        
        self.context_entries.append(entry)
        
        # Trim context if too large
        await self._trim_context()
        
        # Save context
        await self._save_context()
        
        # Log to conversation history if relevant
        if context_type in [ContextType.CONVERSATION, ContextType.FINDINGS]:
            await self._log_to_history(entry)
        
        return entry_id
    
    async def get_context_for_agent(self, 
                                   agent: str,
                                   context_types: List[ContextType] = None,
                                   max_entries: int = 50) -> List[ContextEntry]:
        """
        Get relevant context for an agent.
        
        Args:
            agent: Agent requesting context
            context_types: Types of context to include
            max_entries: Maximum number of entries
        
        Returns:
            List of context entries
        """
        relevant_entries = []
        
        # Sort by importance and recency
        sorted_entries = sorted(
            self.context_entries,
            key=lambda x: (x.importance, x.timestamp),
            reverse=True
        )
        
        for entry in sorted_entries:
            # Filter by type if specified
            if context_types and entry.type not in context_types:
                continue
            
            # Include if from same agent or tagged for sharing
            if entry.agent == agent or 'shared' in entry.tags:
                relevant_entries.append(entry)
            
            if len(relevant_entries) >= max_entries:
                break
        
        return relevant_entries
    
    async def update_agent_memory(self,
                                 agent: str,
                                 current_task: Optional[str] = None,
                                 understanding_update: Dict[str, Any] = None,
                                 new_uncertainty: Optional[str] = None,
                                 new_decision: Optional[Dict[str, Any]] = None,
                                 question_for_peer: Optional[str] = None):
        """
        Update agent's working memory.
        
        Args:
            agent: Agent name
            current_task: Current task description
            understanding_update: Updates to understanding
            new_uncertainty: New uncertainty to track
            new_decision: New decision made
            question_for_peer: Question for other agent
        """
        memory = self.agent_memories.get(agent)
        if not memory:
            memory = AgentMemory(agent)
            self.agent_memories[agent] = memory
        
        if current_task is not None:
            memory.current_task = current_task
        
        if understanding_update:
            memory.understanding.update(understanding_update)
        
        if new_uncertainty:
            memory.uncertainties.append(new_uncertainty)
        
        if new_decision:
            memory.decisions_made.append({
                'timestamp': datetime.now().isoformat(),
                'decision': new_decision
            })
        
        if question_for_peer:
            memory.questions_for_peer.append(question_for_peer)
        
        # Save memory
        await self._save_agent_memory(agent)
    
    async def get_peer_questions(self, for_agent: str) -> List[str]:
        """
        Get questions from peer agent.
        
        Args:
            for_agent: Agent to get questions for
        
        Returns:
            List of questions
        """
        peer_agent = 'gemini' if for_agent == 'claude' else 'claude'
        peer_memory = self.agent_memories.get(peer_agent)
        
        if peer_memory:
            questions = peer_memory.questions_for_peer.copy()
            # Clear questions after retrieval
            peer_memory.questions_for_peer.clear()
            await self._save_agent_memory(peer_agent)
            return questions
        
        return []
    
    async def create_handoff_context(self, 
                                    from_agent: str,
                                    to_agent: str,
                                    task_description: str) -> Dict[str, Any]:
        """
        Create context for task handoff between agents.
        
        Args:
            from_agent: Agent handing off
            to_agent: Agent receiving
            task_description: Description of task
        
        Returns:
            Handoff context
        """
        from_memory = self.agent_memories.get(from_agent)
        
        handoff = {
            'from': from_agent,
            'to': to_agent,
            'timestamp': datetime.now().isoformat(),
            'task': task_description,
            'current_understanding': from_memory.understanding if from_memory else {},
            'uncertainties': from_memory.uncertainties if from_memory else [],
            'decisions_made': from_memory.decisions_made[-5:] if from_memory else [],  # Last 5
            'relevant_context': []
        }
        
        # Add relevant context entries
        recent_context = await self.get_context_for_agent(
            to_agent,
            context_types=[ContextType.TASK, ContextType.FINDINGS],
            max_entries=10
        )
        
        for entry in recent_context:
            handoff['relevant_context'].append({
                'type': entry.type.value,
                'timestamp': entry.timestamp.isoformat(),
                'summary': self._summarize_content(entry.content)
            })
        
        # Save handoff as context
        await self.add_context(
            from_agent,
            ContextType.TASK,
            handoff,
            tags=['handoff', 'shared'],
            importance=8
        )
        
        return handoff
    
    async def _trim_context(self):
        """Trim context to stay within size limits."""
        # Simple trimming based on importance and age
        if len(self.context_entries) > 100:
            # Keep high importance entries
            important_entries = [e for e in self.context_entries if e.importance >= 7]
            
            # Keep recent entries
            recent_entries = sorted(
                [e for e in self.context_entries if e.importance < 7],
                key=lambda x: x.timestamp,
                reverse=True
            )[:50]
            
            self.context_entries = important_entries + recent_entries
    
    async def _save_context(self):
        """Save current context to file."""
        context_data = {
            'timestamp': datetime.now().isoformat(),
            'entries': []
        }
        
        for entry in self.context_entries:
            entry_dict = asdict(entry)
            entry_dict['type'] = entry.type.value
            entry_dict['timestamp'] = entry.timestamp.isoformat()
            context_data['entries'].append(entry_dict)
        
        async with aiofiles.open(self.files['current'], 'w') as f:
            await f.write(json.dumps(context_data, indent=2))
    
    async def _save_agent_memory(self, agent: str):
        """Save agent memory to file."""
        memory = self.agent_memories.get(agent)
        if not memory:
            return
        
        memory_file = self.files.get(f'{agent}_memory')
        if not memory_file:
            return
        
        memory_data = {
            'agent_name': memory.agent_name,
            'current_task': memory.current_task,
            'understanding': memory.understanding,
            'uncertainties': memory.uncertainties,
            'decisions_made': memory.decisions_made,
            'questions_for_peer': memory.questions_for_peer
        }
        
        async with aiofiles.open(memory_file, 'w') as f:
            await f.write(json.dumps(memory_data, indent=2))
    
    async def _log_to_history(self, entry: ContextEntry):
        """Log entry to conversation history."""
        history_entry = {
            'timestamp': entry.timestamp.isoformat(),
            'agent': entry.agent,
            'type': entry.type.value,
            'summary': self._summarize_content(entry.content)
        }
        
        async with aiofiles.open(self.files['conversation_history'], 'a') as f:
            await f.write(json.dumps(history_entry) + '\n')
    
    def _summarize_content(self, content: Dict[str, Any]) -> str:
        """Create brief summary of content."""
        # Simple summarization - in production, could use LLM
        if 'message' in content:
            return content['message'][:100] + '...' if len(content['message']) > 100 else content['message']
        elif 'findings' in content:
            return f"Findings: {len(content['findings'])} items"
        elif 'code' in content:
            return f"Code: {content.get('language', 'unknown')} - {len(content['code'])} chars"
        else:
            return f"Content with {len(content)} fields"
    
    async def get_shared_understanding(self) -> Dict[str, Any]:
        """Get current shared understanding between agents."""
        claude_memory = self.agent_memories.get('claude')
        gemini_memory = self.agent_memories.get('gemini')
        
        shared = {
            'last_updated': datetime.now().isoformat(),
            'current_tasks': {
                'claude': claude_memory.current_task if claude_memory else None,
                'gemini': gemini_memory.current_task if gemini_memory else None
            },
            'combined_understanding': {},
            'pending_questions': {
                'for_claude': await self.get_peer_questions('claude'),
                'for_gemini': await self.get_peer_questions('gemini')
            },
            'recent_decisions': []
        }
        
        # Merge understanding
        if claude_memory:
            shared['combined_understanding'].update(claude_memory.understanding)
        if gemini_memory:
            for key, value in gemini_memory.understanding.items():
                if key in shared['combined_understanding']:
                    # Merge or flag conflicts
                    shared['combined_understanding'][f"{key}_gemini"] = value
                else:
                    shared['combined_understanding'][key] = value
        
        # Collect recent decisions
        all_decisions = []
        if claude_memory:
            all_decisions.extend([{'agent': 'claude', **d} for d in claude_memory.decisions_made])
        if gemini_memory:
            all_decisions.extend([{'agent': 'gemini', **d} for d in gemini_memory.decisions_made])
        
        shared['recent_decisions'] = sorted(
            all_decisions,
            key=lambda x: x.get('timestamp', ''),
            reverse=True
        )[:10]
        
        # Save shared understanding
        async with aiofiles.open(self.files['shared_understanding'], 'w') as f:
            await f.write(json.dumps(shared, indent=2))
        
        return shared