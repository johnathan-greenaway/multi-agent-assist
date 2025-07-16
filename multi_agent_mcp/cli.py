"""
Command-line interface for the Multi-Agent MCP system.
"""
import asyncio
import argparse
import sys
import json
from pathlib import Path
from typing import Dict, Any

from .core.mcp_server import MultiAgentMCPServer, run_mcp_server
from .monitor import main as monitor_main


def start_server(args):
    """Start the MCP server."""
    print(f"Starting Multi-Agent MCP Server with workspace: {args.workspace}")
    asyncio.run(run_mcp_server())


def monitor(args):
    """Start the monitoring dashboard."""
    sys.argv = ['monitor']  # Clear args for monitor
    if args.workspace:
        sys.argv.extend(['--workspace', args.workspace])
    if args.refresh:
        sys.argv.extend(['--refresh', str(args.refresh)])
    if args.watch:
        sys.argv.extend(['--watch', args.watch])
    
    monitor_main()


def init_workspace(args):
    """Initialize a new workspace."""
    workspace_path = Path(args.workspace)
    workspace_path.mkdir(exist_ok=True, parents=True)
    
    # Create directory structure
    dirs = ['tasks', 'findings', 'logs', 'context', 'shared', 'sandbox', 'history', 'claude_workspace', 'gemini_workspace']
    for dir_name in dirs:
        (workspace_path / dir_name).mkdir(exist_ok=True)
    
    # Create initial context files
    context_dir = workspace_path / 'context'
    
    # Shared context
    shared_context = {
        "project_info": {},
        "ongoing_tasks": [],
        "completed_tasks": []
    }
    with open(context_dir / 'shared_context.json', 'w') as f:
        json.dump(shared_context, f, indent=2)
    
    # Agent memories
    for agent in ['claude', 'gemini']:
        memory = {
            "agent_name": agent,
            "current_task": None,
            "understanding": {},
            "uncertainties": [],
            "decisions_made": [],
            "questions_for_peer": []
        }
        with open(context_dir / f'{agent}_memory.json', 'w') as f:
            json.dump(memory, f, indent=2)
    
    # Shared understanding
    understanding = {
        "last_updated": None,
        "current_tasks": {"claude": None, "gemini": None},
        "combined_understanding": {},
        "pending_questions": {"for_claude": [], "for_gemini": []},
        "recent_decisions": []
    }
    with open(context_dir / 'shared_understanding.json', 'w') as f:
        json.dump(understanding, f, indent=2)
    
    print(f"✅ Workspace initialized at: {workspace_path}")
    print("📁 Created directories:")
    for dir_name in dirs:
        print(f"   - {dir_name}/")
    print("\n🔧 Next steps:")
    print(f"   1. Configure Claude Code MCP settings to point to this workspace")
    print(f"   2. Start the server: multi-agent-mcp start --workspace {workspace_path}")
    print(f"   3. Monitor activity: mcp-monitor --workspace {workspace_path}")


def status(args):
    """Show workspace status."""
    workspace_path = Path(args.workspace)
    if not workspace_path.exists():
        print(f"❌ Workspace not found: {workspace_path}")
        return
    
    print(f"📊 Workspace Status: {workspace_path}")
    print("=" * 50)
    
    # Check directories
    dirs = ['tasks', 'findings', 'logs', 'context', 'shared', 'sandbox']
    for dir_name in dirs:
        dir_path = workspace_path / dir_name
        if dir_path.exists():
            file_count = len(list(dir_path.glob('*')))
            print(f"✅ {dir_name:12} - {file_count} files")
        else:
            print(f"❌ {dir_name:12} - missing")
    
    # Check recent activity
    logs_dir = workspace_path / 'logs'
    if logs_dir.exists():
        event_files = list(logs_dir.glob('events_*.jsonl'))
        if event_files:
            latest_event_file = max(event_files, key=lambda x: x.stat().st_mtime)
            print(f"\n📝 Latest activity log: {latest_event_file.name}")
        
        log_files = list(logs_dir.glob('*.log'))
        if log_files:
            latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
            print(f"📋 Server log: {latest_log.name}")
    
    # Context status
    context_dir = workspace_path / 'context'
    if context_dir.exists():
        context_files = ['shared_context.json', 'claude_memory.json', 'gemini_memory.json', 'shared_understanding.json']
        print("\n🧠 Context Files:")
        for file_name in context_files:
            file_path = context_dir / file_name
            if file_path.exists():
                try:
                    with open(file_path) as f:
                        data = json.load(f)
                    print(f"   ✅ {file_name}")
                except:
                    print(f"   ⚠️  {file_name} (corrupted)")
            else:
                print(f"   ❌ {file_name}")


def generate_config(args):
    """Generate MCP configuration for Claude Code."""
    workspace_path = Path(args.workspace).absolute()
    
    config = {
        "mcpServers": {
            "multi-agent": {
                "command": "python",
                "args": ["-m", "multi_agent_mcp.core.mcp_server"],
                "env": {
                    "WORKSPACE_PATH": str(workspace_path)
                }
            }
        }
    }
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✅ Configuration saved to: {args.output}")
    else:
        print("📋 Claude Code MCP Configuration:")
        print(json.dumps(config, indent=2))
        print(f"\n💡 Add this to your Claude Code settings file")


def clean_workspace(args):
    """Clean up workspace files."""
    workspace_path = Path(args.workspace)
    if not workspace_path.exists():
        print(f"❌ Workspace not found: {workspace_path}")
        return
    
    # Ask for confirmation
    if not args.force:
        response = input(f"⚠️  This will clean up files in {workspace_path}. Continue? (y/N): ")
        if response.lower() != 'y':
            print("❌ Cancelled")
            return
    
    cleaned_count = 0
    
    # Clean logs older than specified days
    logs_dir = workspace_path / 'logs'
    if logs_dir.exists():
        import time
        cutoff_time = time.time() - (args.days * 24 * 3600)
        
        for log_file in logs_dir.glob('*.log'):
            if log_file.stat().st_mtime < cutoff_time:
                log_file.unlink()
                cleaned_count += 1
        
        for event_file in logs_dir.glob('events_*.jsonl'):
            if event_file.stat().st_mtime < cutoff_time:
                event_file.unlink()
                cleaned_count += 1
    
    # Clean old findings
    findings_dir = workspace_path / 'findings'
    if findings_dir.exists() and args.clean_findings:
        import time
        cutoff_time = time.time() - (args.days * 24 * 3600)
        
        for finding_file in findings_dir.glob('*.md'):
            if finding_file.stat().st_mtime < cutoff_time:
                finding_file.unlink()
                cleaned_count += 1
    
    # Clean sandbox
    sandbox_dir = workspace_path / 'sandbox'
    if sandbox_dir.exists() and args.clean_sandbox:
        for sandbox_file in sandbox_dir.glob('*'):
            if sandbox_file.is_file():
                sandbox_file.unlink()
                cleaned_count += 1
    
    print(f"✅ Cleaned {cleaned_count} files from workspace")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Multi-Agent MCP Command Line Interface")
    parser.add_argument("--workspace", default="./agent_workspace", help="Workspace directory")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start server command
    start_parser = subparsers.add_parser("start", help="Start the MCP server")
    start_parser.set_defaults(func=start_server)
    
    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Start monitoring dashboard")
    monitor_parser.add_argument("--refresh", type=float, default=1.0, help="Refresh rate")
    monitor_parser.add_argument("--watch", help="Watch specific file")
    monitor_parser.set_defaults(func=monitor)
    
    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize workspace")
    init_parser.set_defaults(func=init_workspace)
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show workspace status")
    status_parser.set_defaults(func=status)
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Generate MCP configuration")
    config_parser.add_argument("--output", help="Output file for configuration")
    config_parser.set_defaults(func=generate_config)
    
    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean workspace")
    clean_parser.add_argument("--days", type=int, default=7, help="Clean files older than N days")
    clean_parser.add_argument("--force", action="store_true", help="Skip confirmation")
    clean_parser.add_argument("--clean-findings", action="store_true", help="Also clean findings")
    clean_parser.add_argument("--clean-sandbox", action="store_true", help="Also clean sandbox")
    clean_parser.set_defaults(func=clean_workspace)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    # Set workspace environment variable
    import os
    os.environ['WORKSPACE_PATH'] = str(Path(args.workspace).absolute())
    
    args.func(args)


if __name__ == "__main__":
    main()