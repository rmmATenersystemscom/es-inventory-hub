#!/usr/bin/env python3
"""
Parse Claude Code session transcripts to show which commands prompted for permission.

Usage:
    python3 show-permission-prompts.py                    # Most recent session
    python3 show-permission-prompts.py [transcript-file]  # Specific session
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


def find_recent_transcript() -> Path:
    """Find the most recent transcript file."""
    transcript_files = list(CLAUDE_PROJECTS_DIR.rglob("transcript-*.jsonl"))
    if not transcript_files:
        return None
    
    # Sort by modification time, most recent first
    return max(transcript_files, key=lambda p: p.stat().st_mtime)


def parse_transcript(file_path: Path) -> List[Dict[str, Any]]:
    """Parse JSONL transcript file and extract permission-related events."""
    permission_events = []
    
    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                event = json.loads(line)
                
                # Look for tool use events (bash commands, file operations)
                if event.get('type') == 'tool_use':
                    permission_events.append({
                        'line': line_num,
                        'type': 'tool_use',
                        'tool': event.get('name', 'unknown'),
                        'input': event.get('input', {}),
                        'timestamp': event.get('timestamp')
                    })
                
                # Look for permission confirmation messages
                elif 'content' in event:
                    content_str = str(event.get('content', ''))
                    if any(keyword in content_str.lower() for keyword in 
                           ['permission', 'proceed', 'do you want', 'confirm']):
                        permission_events.append({
                            'line': line_num,
                            'type': 'confirmation',
                            'content': content_str[:200],  # Truncate long messages
                            'timestamp': event.get('timestamp')
                        })
                
            except json.JSONDecodeError:
                continue
    
    return permission_events


def format_event(event: Dict[str, Any]) -> str:
    """Format a permission event for display."""
    output = []
    
    if event['type'] == 'tool_use':
        tool = event['tool']
        output.append(f"🔧 Tool: {tool}")
        
        # Special formatting for bash commands
        if tool == 'bash_tool':
            cmd = event['input'].get('command', 'N/A')
            desc = event['input'].get('description', '')
            output.append(f"   Command: {cmd}")
            if desc:
                output.append(f"   Why: {desc}")
        else:
            # Format other tool inputs nicely
            for key, value in event['input'].items():
                if isinstance(value, str) and len(value) < 100:
                    output.append(f"   {key}: {value}")
    
    elif event['type'] == 'confirmation':
        output.append(f"❓ Confirmation Request")
        output.append(f"   {event['content']}")
    
    if event.get('timestamp'):
        output.append(f"   Time: {event['timestamp']}")
    
    output.append(f"   (Line {event['line']} in transcript)")
    
    return '\n'.join(output)


def main():
    # Determine which transcript to analyze
    if len(sys.argv) > 1:
        transcript_path = Path(sys.argv[1])
    else:
        transcript_path = find_recent_transcript()
        if not transcript_path:
            print(f"Error: No transcript files found in {CLAUDE_PROJECTS_DIR}")
            sys.exit(1)
        print(f"Analyzing most recent session:")
        print(f"{transcript_path}")
        print()
    
    # Check if file exists
    if not transcript_path.exists():
        print(f"Error: File not found: {transcript_path}")
        sys.exit(1)
    
    # Parse the transcript
    print("Commands and Permission Prompts:")
    print("=" * 60)
    print()
    
    events = parse_transcript(transcript_path)
    
    if not events:
        print("No permission-related events found in this session.")
        print()
        print("This could mean:")
        print("  - All commands were auto-allowed by your settings")
        print("  - Session used --dangerously-skip-permissions")
        print("  - Session is empty or very short")
    else:
        for i, event in enumerate(events, 1):
            print(f"{i}. {format_event(event)}")
            print()
    
    print("-" * 60)
    print(f"Total events found: {len(events)}")
    print(f"Session file: {transcript_path}")
    print()
    print("💡 Tips:")
    print("  - Add frequently prompted commands to your settings.json 'allow' list")
    print("  - Use /permissions during a session for interactive permission management")
    print("  - To see all sessions: ls -lht ~/.claude/projects/*/transcript-*.jsonl")


if __name__ == "__main__":
    main()
