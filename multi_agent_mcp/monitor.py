"""
Enhanced real-time monitoring dashboard for multi-agent interactions.
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime
import time
import sys
import argparse
from collections import deque, defaultdict
from typing import Dict, List, Any, Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.text import Text
    from rich.syntax import Syntax
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.columns import Columns
except ImportError:
    print("Please install rich: pip install rich")
    sys.exit(1)


class EnhancedAgentMonitor:
    """Enhanced monitoring with real-time updates and detailed insights."""
    
    def __init__(self, workspace_dir: str = "./agent_workspace", refresh_rate: float = 1.0):
        self.workspace_dir = Path(workspace_dir)
        self.console = Console()
        self.refresh_rate = refresh_rate
        
        # Tracking data structures
        self.task_history = deque(maxlen=100)
        self.agent_metrics = defaultdict(lambda: {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'total_time': 0,
            'last_active': None
        })
        self.active_sessions = {}
        self.file_activity = deque(maxlen=50)
        
        # Verify workspace
        if not self.workspace_dir.exists():
            self.console.print(f"[red]Creating workspace directory: {workspace_dir}[/red]")
            self.workspace_dir.mkdir(parents=True)
            for subdir in ['tasks', 'findings', 'logs', 'context', 'shared', 'sandbox']:
                (self.workspace_dir / subdir).mkdir(exist_ok=True)
    
    def get_recent_tasks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent tasks with enhanced metadata."""
        tasks = []
        
        # Scan task directory
        task_dir = self.workspace_dir / "tasks"
        if not task_dir.exists():
            return tasks
        
        task_files = sorted(
            task_dir.glob("*.md"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[:limit]
        
        for task_file in task_files:
            # Parse task ID and type
            parts = task_file.stem.split('_', 2)
            task_id = parts[0] if parts else task_file.stem
            task_type = parts[1] if len(parts) > 1 else "unknown"
            
            # Get task metadata
            try:
                content = task_file.read_text()
                # Extract query or description
                query = "No description"
                if "Query:" in content:
                    query = content.split("Query:")[1].split('\n')[0].strip()
                elif "Description:" in content:
                    query = content.split("Description:")[1].split('\n')[0].strip()
                
                # Get status from logs
                log_file = self.workspace_dir / "logs" / f"{task_id}_log.json"
                status = "pending"
                agent = "unknown"
                duration = None
                
                if log_file.exists():
                    try:
                        logs = json.loads(log_file.read_text())
                        if logs:
                            status = logs[-1].get("status", "unknown")
                            agent = logs[0].get("agent", "unknown")
                            
                            # Calculate duration
                            if len(logs) > 1 and logs[-1].get("status") == "completed":
                                start = datetime.fromisoformat(logs[0]["timestamp"])
                                end = datetime.fromisoformat(logs[-1]["timestamp"])
                                duration = (end - start).total_seconds()
                    except:
                        pass
                
                # Check for findings
                findings_file = self.workspace_dir / "findings" / f"{task_id}_findings.md"
                has_findings = findings_file.exists()
                
                tasks.append({
                    "id": task_id,
                    "type": task_type,
                    "query": query[:50] + "..." if len(query) > 50 else query,
                    "status": status,
                    "agent": agent,
                    "created": datetime.fromtimestamp(task_file.stat().st_mtime),
                    "duration": duration,
                    "has_findings": has_findings,
                    "file": task_file.name
                })
                
                # Update metrics
                if status == "completed":
                    self.agent_metrics[agent]['tasks_completed'] += 1
                    if duration:
                        self.agent_metrics[agent]['total_time'] += duration
                elif status == "failed":
                    self.agent_metrics[agent]['tasks_failed'] += 1
                
                self.agent_metrics[agent]['last_active'] = datetime.now()
                
            except Exception as e:
                self.console.print(f"[red]Error parsing task {task_file}: {e}[/red]")
        
        return tasks
    
    def get_context_info(self) -> Dict[str, Any]:
        """Get enhanced context information."""
        context = {}
        
        # Shared context
        context_file = self.workspace_dir / "context" / "shared_context.json"
        if context_file.exists():
            try:
                context['shared'] = json.loads(context_file.read_text())
            except:
                context['shared'] = {}
        
        # Agent memories
        for agent in ['claude', 'gemini']:
            memory_file = self.workspace_dir / "context" / f"{agent}_memory.json"
            if memory_file.exists():
                try:
                    context[f'{agent}_memory'] = json.loads(memory_file.read_text())
                except:
                    context[f'{agent}_memory'] = {}
        
        # Shared understanding
        understanding_file = self.workspace_dir / "context" / "shared_understanding.json"
        if understanding_file.exists():
            try:
                context['understanding'] = json.loads(understanding_file.read_text())
            except:
                context['understanding'] = {}
        
        return context
    
    def get_workspace_activity(self) -> List[Dict[str, Any]]:
        """Get recent workspace file activity."""
        activity = []
        
        # Check event logs
        log_dir = self.workspace_dir / "logs"
        if log_dir.exists():
            event_files = sorted(
                log_dir.glob("events_*.jsonl"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )[:3]  # Last 3 days
            
            for event_file in event_files:
                try:
                    with open(event_file, 'r') as f:
                        for line in f:
                            event = json.loads(line)
                            activity.append(event)
                            if len(activity) >= 20:  # Limit
                                return activity
                except:
                    pass
        
        return activity
    
    def create_dashboard(self) -> Layout:
        """Create comprehensive monitoring dashboard."""
        layout = Layout()
        
        # Get data
        tasks = self.get_recent_tasks()
        context = self.get_context_info()
        activity = self.get_workspace_activity()
        
        # Create header
        header_text = Text("Multi-Agent Collaboration Monitor", style="bold blue", justify="center")
        header_text.append(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim")
        header = Panel(header_text, style="blue")
        
        # Create metrics panel
        metrics_content = self._create_metrics_panel(tasks)
        
        # Create tasks table
        tasks_table = self._create_tasks_table(tasks[:10])
        
        # Create agent status panels
        claude_panel = self._create_agent_panel("Claude", context.get('claude_memory', {}))
        gemini_panel = self._create_agent_panel("Gemini", context.get('gemini_memory', {}))
        
        # Create activity feed
        activity_panel = self._create_activity_panel(activity[:10])
        
        # Create understanding panel
        understanding_panel = self._create_understanding_panel(context.get('understanding', {}))
        
        # Layout assembly
        layout.split_column(
            Layout(header, size=4),
            Layout(name="main")
        )
        
        layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )
        
        layout["main"]["left"].split_column(
            Layout(metrics_content, size=8),
            Layout(tasks_table),
            Layout(activity_panel, size=12)
        )
        
        layout["main"]["right"].split_column(
            Layout(claude_panel, size=12),
            Layout(gemini_panel, size=12),
            Layout(understanding_panel)
        )
        
        return layout
    
    def _create_metrics_panel(self, tasks: List[Dict[str, Any]]) -> Panel:
        """Create metrics summary panel."""
        total_tasks = len(tasks)
        completed = sum(1 for t in tasks if t["status"] == "completed")
        failed = sum(1 for t in tasks if t["status"] == "failed")
        active = sum(1 for t in tasks if t["status"] in ["started", "pending"])
        
        # Calculate success rate
        success_rate = (completed / total_tasks * 100) if total_tasks > 0 else 0
        
        # Agent breakdown
        claude_tasks = sum(1 for t in tasks if t.get("agent") == "claude")
        gemini_tasks = sum(1 for t in tasks if t.get("agent") == "gemini")
        
        metrics_text = f"""[bold green]Active Tasks:[/bold green] {active}  [bold blue]Completed:[/bold blue] {completed}  [bold red]Failed:[/bold red] {failed}
[bold yellow]Total Tasks:[/bold yellow] {total_tasks}  [bold cyan]Success Rate:[/bold cyan] {success_rate:.1f}%

[bold]Agent Distribution:[/bold]  Claude: {claude_tasks}  Gemini: {gemini_tasks}"""
        
        return Panel(metrics_text, title="System Metrics", border_style="green")
    
    def _create_tasks_table(self, tasks: List[Dict[str, Any]]) -> Panel:
        """Create detailed tasks table."""
        table = Table(show_header=True, header_style="bold magenta", expand=True)
        table.add_column("ID", style="cyan", width=8)
        table.add_column("Type", style="yellow", width=15)
        table.add_column("Query", style="white", width=30)
        table.add_column("Agent", style="blue", width=8)
        table.add_column("Status", width=10)
        table.add_column("Duration", style="green", width=10)
        table.add_column("Findings", width=8)
        
        for task in tasks:
            # Status styling
            status_style = {
                "completed": "[green]✓ Done[/green]",
                "started": "[yellow]⚡ Active[/yellow]",
                "pending": "[dim]⏳ Wait[/dim]",
                "failed": "[red]✗ Failed[/red]"
            }.get(task["status"], task["status"])
            
            # Duration formatting
            duration_str = "In progress"
            if task["duration"] is not None:
                if task["duration"] < 60:
                    duration_str = f"{task['duration']:.1f}s"
                else:
                    duration_str = f"{task['duration']/60:.1f}m"
            
            # Findings indicator
            findings_str = "[green]✓[/green]" if task["has_findings"] else "[red]✗[/red]"
            
            table.add_row(
                task["id"],
                task["type"],
                task["query"],
                task["agent"],
                status_style,
                duration_str,
                findings_str
            )
        
        return Panel(table, title="Recent Tasks", border_style="magenta")
    
    def _create_agent_panel(self, agent_name: str, memory: Dict[str, Any]) -> Panel:
        """Create agent status panel."""
        content = f"[bold]{agent_name} Status[/bold]\n\n"
        
        # Current task
        current_task = memory.get('current_task', 'None')
        content += f"[yellow]Current Task:[/yellow] {current_task}\n"
        
        # Uncertainties
        uncertainties = memory.get('uncertainties', [])
        if uncertainties:
            content += f"\n[red]Uncertainties:[/red]\n"
            for u in uncertainties[-3:]:  # Last 3
                content += f"  • {u[:50]}...\n" if len(u) > 50 else f"  • {u}\n"
        
        # Questions for peer
        questions = memory.get('questions_for_peer', [])
        if questions:
            content += f"\n[cyan]Questions:[/cyan]\n"
            for q in questions[-2:]:  # Last 2
                content += f"  ? {q[:50]}...\n" if len(q) > 50 else f"  ? {q}\n"
        
        # Metrics
        metrics = self.agent_metrics[agent_name.lower()]
        if metrics['last_active']:
            time_ago = (datetime.now() - metrics['last_active']).total_seconds()
            if time_ago < 60:
                active_str = f"{time_ago:.0f}s ago"
            else:
                active_str = f"{time_ago/60:.0f}m ago"
            content += f"\n[dim]Last active: {active_str}[/dim]"
        
        color = "blue" if agent_name == "Claude" else "green"
        return Panel(content, title=f"{agent_name} Agent", border_style=color)
    
    def _create_activity_panel(self, activity: List[Dict[str, Any]]) -> Panel:
        """Create file activity panel."""
        content = ""
        
        for event in activity[:8]:  # Show last 8
            timestamp = datetime.fromisoformat(event['timestamp'])
            time_str = timestamp.strftime('%H:%M:%S')
            
            # Format based on action
            action_icon = {
                'acquired': '🔒',
                'released': '🔓',
                'read': '👁️',
                'wrote': '✏️',
                'created': '➕'
            }.get(event['action'], '•')
            
            agent_color = "blue" if event['agent'] == 'claude' else "green"
            
            content += f"[dim]{time_str}[/dim] {action_icon} [{agent_color}]{event['agent']}[/{agent_color}] "
            content += f"{event['action']} [yellow]{event['file']}[/yellow]\n"
        
        return Panel(content or "No recent activity", title="File Activity", border_style="yellow")
    
    def _create_understanding_panel(self, understanding: Dict[str, Any]) -> Panel:
        """Create shared understanding panel."""
        content = "[bold]Shared Understanding[/bold]\n\n"
        
        # Current tasks
        tasks = understanding.get('current_tasks', {})
        if tasks.get('claude') or tasks.get('gemini'):
            content += "[yellow]Active Tasks:[/yellow]\n"
            if tasks.get('claude'):
                content += f"  Claude: {tasks['claude'][:40]}...\n"
            if tasks.get('gemini'):
                content += f"  Gemini: {tasks['gemini'][:40]}...\n"
            content += "\n"
        
        # Recent decisions
        decisions = understanding.get('recent_decisions', [])
        if decisions:
            content += "[cyan]Recent Decisions:[/cyan]\n"
            for decision in decisions[:3]:
                agent = decision.get('agent', 'unknown')
                desc = str(decision.get('decision', {})).get('description', 'No description')[:40]
                content += f"  • [{agent}] {desc}...\n"
        
        # Combined understanding keys
        combined = understanding.get('combined_understanding', {})
        if combined:
            content += f"\n[green]Knowledge Base:[/green] {len(combined)} entries"
        
        return Panel(content, title="Collaboration State", border_style="cyan")
    
    def watch_file(self, filepath: str):
        """Watch a specific file for changes."""
        file_path = Path(filepath)
        if not file_path.exists():
            self.console.print(f"[red]File not found: {filepath}[/red]")
            return
        
        last_modified = 0
        with Live(console=self.console, refresh_per_second=self.refresh_rate) as live:
            while True:
                try:
                    current_modified = file_path.stat().st_mtime
                    if current_modified != last_modified:
                        last_modified = current_modified
                        content = file_path.read_text()
                        
                        # Syntax highlighting
                        if filepath.endswith('.json'):
                            try:
                                # Pretty print JSON
                                data = json.loads(content)
                                content = json.dumps(data, indent=2)
                            except:
                                pass
                            syntax = Syntax(content, "json", theme="monokai", line_numbers=True)
                        elif filepath.endswith('.md'):
                            syntax = Syntax(content, "markdown", theme="monokai", line_numbers=True)
                        elif filepath.endswith('.py'):
                            syntax = Syntax(content, "python", theme="monokai", line_numbers=True)
                        else:
                            syntax = Text(content)
                        
                        panel = Panel(
                            syntax,
                            title=f"Watching: {filepath}",
                            subtitle=f"Modified: {datetime.fromtimestamp(current_modified).strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        live.update(panel)
                    
                    time.sleep(self.refresh_rate)
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.console.print(f"[red]Error: {e}[/red]")
                    break
    
    def run_live_monitor(self):
        """Run live monitoring dashboard."""
        self.console.print("[bold green]Starting Multi-Agent Monitor...[/bold green]")
        self.console.print(f"[yellow]Workspace: {self.workspace_dir}[/yellow]")
        self.console.print("[dim]Press Ctrl+C to exit[/dim]\n")
        
        with Live(self.create_dashboard(), refresh_per_second=self.refresh_rate) as live:
            try:
                while True:
                    time.sleep(self.refresh_rate)
                    live.update(self.create_dashboard())
            except KeyboardInterrupt:
                self.console.print("\n[bold red]Monitor stopped.[/bold red]")


def main():
    """Main entry point for the monitor."""
    parser = argparse.ArgumentParser(description="Monitor multi-agent collaboration")
    parser.add_argument(
        "--workspace",
        default="./agent_workspace",
        help="Path to agent workspace directory"
    )
    parser.add_argument(
        "--refresh",
        type=float,
        default=1.0,
        help="Refresh rate in seconds"
    )
    parser.add_argument(
        "--watch",
        help="Watch a specific file instead of dashboard"
    )
    
    args = parser.parse_args()
    
    monitor = EnhancedAgentMonitor(
        workspace_dir=args.workspace,
        refresh_rate=args.refresh
    )
    
    if args.watch:
        monitor.watch_file(args.watch)
    else:
        monitor.run_live_monitor()


if __name__ == "__main__":
    main()