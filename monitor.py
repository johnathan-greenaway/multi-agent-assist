#!/usr/bin/env python3
"""
Real-time monitoring dashboard for Claude-Gemini agent interactions
"""
import json
from pathlib import Path
from datetime import datetime
import time
import sys
import argparse
from collections import deque

try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.text import Text
    from rich.syntax import Syntax
except ImportError:
    print("Please install rich: pip install rich")
    sys.exit(1)

class AgentMonitor:
    def __init__(self, workspace_dir="./agent_workspace", refresh_rate=1):
        self.workspace_dir = Path(workspace_dir)
        self.console = Console()
        self.refresh_rate = refresh_rate
        self.task_history = deque(maxlen=50)
        
        # Verify workspace exists
        if not self.workspace_dir.exists():
            self.console.print(f"[red]Workspace directory '{workspace_dir}' not found![/red]")
            self.console.print("[yellow]Creating workspace directory...[/yellow]")
            self.workspace_dir.mkdir(parents=True)
            for subdir in ['tasks', 'findings', 'logs', 'context', 'shared']:
                (self.workspace_dir / subdir).mkdir(exist_ok=True)
    
    def get_recent_tasks(self, limit=10):
        """Get recent tasks from both agents"""
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
            # Extract task ID and tool name from filename
            parts = task_file.stem.split('_', 1)
            task_id = parts[0] if parts else task_file.stem
            tool_name = parts[1] if len(parts) > 1 else "unknown"
            
            # Get task details
            content = task_file.read_text()
            
            # Get corresponding log
            log_file = self.workspace_dir / "logs" / f"{task_id}_log.json"
            status = "pending"
            start_time = datetime.fromtimestamp(task_file.stat().st_mtime)
            end_time = None
            
            if log_file.exists():
                try:
                    logs = json.loads(log_file.read_text())
                    if logs:
                        status = logs[-1].get("status", "unknown")
                        if logs[-1].get("status") == "completed":
                            end_time = logs[-1].get("timestamp")
                except:
                    pass
            
            # Check for findings
            findings_file = self.workspace_dir / "findings" / f"{task_id}_findings.md"
            has_findings = findings_file.exists()
            
            tasks.append({
                "id": task_id,
                "tool": tool_name,
                "status": status,
                "created": start_time,
                "completed": end_time,
                "has_findings": has_findings,
                "file": task_file.name
            })
        
        return tasks
    
    def get_context_info(self):
        """Get shared context information"""
        context_file = self.workspace_dir / "context" / "agent_context.json"
        if context_file.exists():
            try:
                return json.loads(context_file.read_text())
            except:
                return {}
        return {}
    
    def get_latest_findings(self, limit=3):
        """Get latest findings snippets"""
        findings_dir = self.workspace_dir / "findings"
        if not findings_dir.exists():
            return []
        
        findings = []
        finding_files = sorted(
            findings_dir.glob("*.md"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[:limit]
        
        for finding_file in finding_files:
            content = finding_file.read_text()
            # Extract executive summary if available
            summary = "No summary available"
            if "## Executive Summary" in content:
                start = content.find("## Executive Summary") + len("## Executive Summary")
                end = content.find("\n##", start)
                if end == -1:
                    end = start + 200
                summary = content[start:end].strip()[:150] + "..."
            
            findings.append({
                "file": finding_file.name,
                "task_id": finding_file.stem.replace("_findings", ""),
                "summary": summary,
                "created": datetime.fromtimestamp(finding_file.stat().st_mtime)
            })
        
        return findings
    
    def create_dashboard(self):
        """Create monitoring dashboard"""
        layout = Layout()
        
        # Get data
        tasks = self.get_recent_tasks()
        context = self.get_context_info()
        findings = self.get_latest_findings()
        
        # Create header
        header = Panel(
            Text("Claude-Gemini Agent Monitoring Dashboard", style="bold blue", justify="center"),
            style="blue"
        )
        
        # Create summary panel
        ongoing = sum(1 for t in tasks if t["status"] == "started")
        completed = sum(1 for t in tasks if t["status"] == "completed")
        
        summary_content = f"""[bold green]Active Tasks:[/bold green] {ongoing}
[bold blue]Completed:[/bold blue] {completed}
[bold yellow]Total Tasks:[/bold yellow] {len(tasks)}
[bold cyan]Last Update:[/bold cyan] {datetime.now().strftime('%H:%M:%S')}"""
        
        summary = Panel(summary_content, title="Summary", border_style="green")
        
        # Create tasks table
        table = Table(title="Recent Tasks", show_header=True, header_style="bold magenta")
        table.add_column("Task ID", style="cyan", width=10)
        table.add_column("Tool", style="yellow", width=20)
        table.add_column("Status", style="green", width=12)
        table.add_column("Duration", style="blue", width=12)
        table.add_column("Findings", style="magenta", width=10)
        
        for task in tasks[:8]:  # Show only 8 most recent
            status_style = {
                "completed": "green",
                "started": "yellow",
                "pending": "red"
            }.get(task["status"], "white")
            
            # Calculate duration
            duration = "In progress"
            if task["status"] == "completed" and task["completed"]:
                try:
                    end = datetime.fromisoformat(task["completed"])
                    duration = str(end - task["created"]).split('.')[0]
                except:
                    duration = "Unknown"
            
            findings_icon = "✓" if task["has_findings"] else "✗"
            findings_style = "green" if task["has_findings"] else "red"
            
            table.add_row(
                task["id"],
                task["tool"],
                f"[{status_style}]{task['status']}[/{status_style}]",
                duration,
                f"[{findings_style}]{findings_icon}[/{findings_style}]"
            )
        
        # Create findings panel
        findings_content = ""
        for finding in findings:
            findings_content += f"[bold cyan]{finding['task_id']}[/bold cyan] - {finding['created'].strftime('%H:%M')}\n"
            findings_content += f"{finding['summary']}\n\n"
        
        findings_panel = Panel(
            findings_content or "No recent findings",
            title="Latest Findings",
            border_style="cyan"
        )
        
        # Create context panel
        ongoing_tasks = context.get("ongoing_tasks", [])[-3:]
        context_content = "[bold]Ongoing Tasks:[/bold]\n"
        for task in ongoing_tasks:
            context_content += f"  • {task.get('tool', 'Unknown')} ({task.get('id', 'Unknown')})\n"
        
        context_panel = Panel(
            context_content,
            title="Agent Context",
            border_style="yellow"
        )
        
        # Layout assembly
        layout.split_column(
            Layout(header, size=3),
            Layout(name="main")
        )
        
        layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )
        
        layout["main"]["left"].split_column(
            Layout(summary, size=6),
            Layout(table)
        )
        
        layout["main"]["right"].split_column(
            Layout(findings_panel),
            Layout(context_panel, size=10)
        )
        
        return layout
    
    def watch_file(self, filepath):
        """Watch a specific file for changes"""
        if not Path(filepath).exists():
            self.console.print(f"[red]File not found: {filepath}[/red]")
            return
        
        last_modified = 0
        with Live(console=self.console, refresh_per_second=self.refresh_rate) as live:
            while True:
                try:
                    current_modified = Path(filepath).stat().st_mtime
                    if current_modified != last_modified:
                        last_modified = current_modified
                        content = Path(filepath).read_text()
                        
                        # Syntax highlighting for different file types
                        if filepath.endswith('.json'):
                            syntax = Syntax(content, "json", theme="monokai")
                        elif filepath.endswith('.md'):
                            syntax = Syntax(content, "markdown", theme="monokai")
                        else:
                            syntax = Text(content)
                        
                        panel = Panel(
                            syntax,
                            title=f"Watching: {filepath}",
                            subtitle=f"Last modified: {datetime.fromtimestamp(current_modified).strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        live.update(panel)
                    
                    time.sleep(self.refresh_rate)
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.console.print(f"[red]Error: {e}[/red]")
                    break
    
    def run_live_monitor(self):
        """Run live monitoring dashboard"""
        self.console.print("[bold green]Starting Agent Monitor...[/bold green]")
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
    parser = argparse.ArgumentParser(description="Monitor Claude-Gemini agent interactions")
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
    
    monitor = AgentMonitor(
        workspace_dir=args.workspace,
        refresh_rate=args.refresh
    )
    
    if args.watch:
        monitor.watch_file(args.watch)
    else:
        monitor.run_live_monitor()

if __name__ == "__main__":
    main()