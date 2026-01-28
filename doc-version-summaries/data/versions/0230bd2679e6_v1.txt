#!/usr/bin/env python3
"""
Document Version Summaries - Auto-generate diff summaries when files change.

Track document versions and generate human-readable summaries of what changed.
Supports code, markdown, JSON, plain text, and more.

Usage:
    python version_tracker.py track <file> [--name <name>]
    python version_tracker.py diff <file> [--v1 <version>] [--v2 <version>]
    python version_tracker.py history <file> [--limit <n>]
    python version_tracker.py summary <file> [--since <date>]
    python version_tracker.py watch <path> [--interval <seconds>]
    python version_tracker.py report [--days <n>]
    python version_tracker.py restore <file> --version <n>
    python version_tracker.py search <query>
    python version_tracker.py stats
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from difflib import unified_diff, SequenceMatcher
from typing import Optional, List, Dict, Any, Tuple


# Data storage
DATA_DIR = Path(__file__).parent / "data"
VERSIONS_DIR = DATA_DIR / "versions"
INDEX_FILE = DATA_DIR / "index.json"
HISTORY_FILE = DATA_DIR / "history.json"


def ensure_data_dirs():
    """Create data directories if they don't exist."""
    DATA_DIR.mkdir(exist_ok=True)
    VERSIONS_DIR.mkdir(exist_ok=True)
    if not INDEX_FILE.exists():
        INDEX_FILE.write_text(json.dumps({"files": {}}, indent=2))
    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text(json.dumps({"changes": []}, indent=2))


def load_index() -> Dict:
    """Load the file index."""
    ensure_data_dirs()
    return json.loads(INDEX_FILE.read_text())


def save_index(index: Dict):
    """Save the file index."""
    INDEX_FILE.write_text(json.dumps(index, indent=2))


def load_history() -> Dict:
    """Load change history."""
    ensure_data_dirs()
    return json.loads(HISTORY_FILE.read_text())


def save_history(history: Dict):
    """Save change history."""
    HISTORY_FILE.write_text(json.dumps(history, indent=2))


def file_hash(filepath: Path) -> str:
    """Calculate SHA256 hash of file contents."""
    content = filepath.read_bytes()
    return hashlib.sha256(content).hexdigest()[:16]


def get_file_id(filepath: Path) -> str:
    """Generate unique ID for a file based on absolute path."""
    abs_path = str(filepath.resolve())
    return hashlib.sha256(abs_path.encode()).hexdigest()[:12]


def detect_file_type(filepath: Path) -> str:
    """Detect file type from extension."""
    ext = filepath.suffix.lower()
    types = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.cs': 'csharp',
        '.rb': 'ruby',
        '.go': 'go',
        '.rs': 'rust',
        '.md': 'markdown',
        '.txt': 'text',
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.xml': 'xml',
        '.html': 'html',
        '.css': 'css',
        '.sql': 'sql',
        '.sh': 'shell',
        '.bat': 'batch',
        '.ps1': 'powershell',
        '.ini': 'ini',
        '.cfg': 'config',
        '.conf': 'config',
        '.env': 'env',
    }
    return types.get(ext, 'text')


def parse_changes(old_content: str, new_content: str, file_type: str) -> Dict[str, Any]:
    """Parse changes between two versions and generate structured analysis."""
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()
    
    # Basic line counts
    added_lines = []
    removed_lines = []
    
    diff = list(unified_diff(old_lines, new_lines, lineterm=''))
    
    for line in diff:
        if line.startswith('+') and not line.startswith('+++'):
            added_lines.append(line[1:])
        elif line.startswith('-') and not line.startswith('---'):
            removed_lines.append(line[1:])
    
    # Similarity ratio
    similarity = SequenceMatcher(None, old_content, new_content).ratio()
    
    # Detect specific change types
    change_types = []
    
    if file_type in ['python', 'javascript', 'typescript', 'java', 'csharp']:
        # Code-specific analysis
        for line in added_lines:
            stripped = line.strip()
            if stripped.startswith(('def ', 'function ', 'func ', 'public ', 'private ', 'class ')):
                change_types.append('new_function_or_class')
            elif stripped.startswith(('import ', 'from ', 'require(', 'using ')):
                change_types.append('dependency_change')
            elif stripped.startswith(('#', '//', '/*', '*', '"""', "'''")):
                change_types.append('comment_added')
        
        for line in removed_lines:
            stripped = line.strip()
            if stripped.startswith(('def ', 'function ', 'func ', 'public ', 'private ', 'class ')):
                change_types.append('removed_function_or_class')
    
    elif file_type == 'markdown':
        # Markdown-specific analysis
        for line in added_lines:
            stripped = line.strip()
            if stripped.startswith('#'):
                change_types.append('heading_added')
            elif stripped.startswith(('- ', '* ', '1.')):
                change_types.append('list_item_added')
            elif '```' in stripped:
                change_types.append('code_block_changed')
    
    elif file_type == 'json':
        # JSON-specific analysis
        try:
            old_json = json.loads(old_content) if old_content.strip() else {}
            new_json = json.loads(new_content) if new_content.strip() else {}
            
            def get_keys(obj, prefix=''):
                keys = set()
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        full_key = f"{prefix}.{k}" if prefix else k
                        keys.add(full_key)
                        keys.update(get_keys(v, full_key))
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        keys.update(get_keys(item, f"{prefix}[{i}]"))
                return keys
            
            old_keys = get_keys(old_json)
            new_keys = get_keys(new_json)
            
            added_keys = new_keys - old_keys
            removed_keys = old_keys - new_keys
            
            if added_keys:
                change_types.append('keys_added')
            if removed_keys:
                change_types.append('keys_removed')
        except json.JSONDecodeError:
            pass
    
    return {
        'lines_added': len(added_lines),
        'lines_removed': len(removed_lines),
        'net_change': len(added_lines) - len(removed_lines),
        'similarity': round(similarity * 100, 1),
        'change_types': list(set(change_types)),
        'added_preview': added_lines[:5],
        'removed_preview': removed_lines[:5]
    }


def generate_summary(changes: Dict[str, Any], file_type: str, filename: str) -> str:
    """Generate human-readable summary of changes."""
    parts = []
    
    # Opening statement
    similarity = changes['similarity']
    if similarity >= 95:
        parts.append(f"Minor edits to **{filename}**")
    elif similarity >= 80:
        parts.append(f"Moderate changes to **{filename}**")
    elif similarity >= 50:
        parts.append(f"Significant updates to **{filename}**")
    else:
        parts.append(f"Major revision of **{filename}**")
    
    # Line counts
    added = changes['lines_added']
    removed = changes['lines_removed']
    if added > 0 and removed > 0:
        parts.append(f"(+{added}/-{removed} lines)")
    elif added > 0:
        parts.append(f"(+{added} lines)")
    elif removed > 0:
        parts.append(f"(-{removed} lines)")
    
    # Change types
    type_descriptions = {
        'new_function_or_class': 'Added new function(s) or class(es)',
        'removed_function_or_class': 'Removed function(s) or class(es)',
        'dependency_change': 'Modified imports/dependencies',
        'comment_added': 'Added comments/documentation',
        'heading_added': 'Added new section(s)',
        'list_item_added': 'Added list items',
        'code_block_changed': 'Modified code examples',
        'keys_added': 'Added new fields',
        'keys_removed': 'Removed fields'
    }
    
    if changes['change_types']:
        parts.append("\n\nChanges:")
        for ct in changes['change_types']:
            if ct in type_descriptions:
                parts.append(f"  • {type_descriptions[ct]}")
    
    # Preview of additions
    if changes['added_preview']:
        parts.append("\n\nKey additions:")
        for line in changes['added_preview'][:3]:
            if line.strip():
                preview = line.strip()[:60]
                if len(line.strip()) > 60:
                    preview += "..."
                parts.append(f"  + {preview}")
    
    return ' '.join(parts[:2]) + ''.join(parts[2:])


def track_file(filepath: Path, name: Optional[str] = None) -> Dict:
    """Track a file and store its current version."""
    if not filepath.exists():
        return {"error": f"File not found: {filepath}"}
    
    index = load_index()
    history = load_history()
    
    file_id = get_file_id(filepath)
    content = filepath.read_text(encoding='utf-8', errors='replace')
    content_hash = file_hash(filepath)
    file_type = detect_file_type(filepath)
    
    now = datetime.now().isoformat()
    
    # Check if file is already tracked
    if file_id in index['files']:
        file_info = index['files'][file_id]
        versions = file_info['versions']
        
        # Check if content actually changed
        if versions and versions[-1]['hash'] == content_hash:
            return {
                "status": "unchanged",
                "file": filepath.name,
                "version": len(versions),
                "message": "No changes detected since last version"
            }
        
        # Get previous content for diff
        prev_version = versions[-1]
        prev_content_path = VERSIONS_DIR / f"{file_id}_v{prev_version['version']}.txt"
        prev_content = prev_content_path.read_text(encoding='utf-8', errors='replace') if prev_content_path.exists() else ""
        
        # Analyze changes
        changes = parse_changes(prev_content, content, file_type)
        summary = generate_summary(changes, file_type, filepath.name)
        
        # Store new version
        new_version = len(versions) + 1
        version_path = VERSIONS_DIR / f"{file_id}_v{new_version}.txt"
        version_path.write_text(content, encoding='utf-8')
        
        version_info = {
            "version": new_version,
            "hash": content_hash,
            "timestamp": now,
            "size": len(content),
            "lines_added": changes['lines_added'],
            "lines_removed": changes['lines_removed'],
            "similarity": changes['similarity'],
            "summary": summary
        }
        
        versions.append(version_info)
        file_info['updated'] = now
        
        # Add to history
        history['changes'].append({
            "file_id": file_id,
            "file": str(filepath),
            "name": file_info.get('name', filepath.name),
            "version": new_version,
            "timestamp": now,
            "summary": summary,
            "lines_added": changes['lines_added'],
            "lines_removed": changes['lines_removed']
        })
        
        save_index(index)
        save_history(history)
        
        return {
            "status": "updated",
            "file": filepath.name,
            "version": new_version,
            "summary": summary,
            "changes": changes
        }
    
    else:
        # New file - start tracking
        version_path = VERSIONS_DIR / f"{file_id}_v1.txt"
        version_path.write_text(content, encoding='utf-8')
        
        index['files'][file_id] = {
            "path": str(filepath.resolve()),
            "name": name or filepath.name,
            "type": file_type,
            "created": now,
            "updated": now,
            "versions": [{
                "version": 1,
                "hash": content_hash,
                "timestamp": now,
                "size": len(content),
                "lines_added": len(content.splitlines()),
                "lines_removed": 0,
                "similarity": 0,
                "summary": f"Initial version of {filepath.name}"
            }]
        }
        
        history['changes'].append({
            "file_id": file_id,
            "file": str(filepath),
            "name": name or filepath.name,
            "version": 1,
            "timestamp": now,
            "summary": f"Started tracking {filepath.name}",
            "lines_added": len(content.splitlines()),
            "lines_removed": 0
        })
        
        save_index(index)
        save_history(history)
        
        return {
            "status": "tracking",
            "file": filepath.name,
            "version": 1,
            "message": f"Now tracking {filepath.name}",
            "type": file_type
        }


def get_diff(filepath: Path, v1: Optional[int] = None, v2: Optional[int] = None) -> Dict:
    """Get diff between two versions of a file."""
    index = load_index()
    file_id = get_file_id(filepath)
    
    if file_id not in index['files']:
        return {"error": f"File not tracked: {filepath}"}
    
    file_info = index['files'][file_id]
    versions = file_info['versions']
    
    if len(versions) < 2:
        return {"error": "Need at least 2 versions to diff"}
    
    # Default to comparing last two versions
    if v1 is None:
        v1 = len(versions) - 1
    if v2 is None:
        v2 = len(versions)
    
    if v1 < 1 or v1 > len(versions) or v2 < 1 or v2 > len(versions):
        return {"error": f"Invalid version numbers. Available: 1-{len(versions)}"}
    
    # Load version contents
    v1_path = VERSIONS_DIR / f"{file_id}_v{v1}.txt"
    v2_path = VERSIONS_DIR / f"{file_id}_v{v2}.txt"
    
    if not v1_path.exists() or not v2_path.exists():
        return {"error": "Version content not found"}
    
    v1_content = v1_path.read_text(encoding='utf-8', errors='replace')
    v2_content = v2_path.read_text(encoding='utf-8', errors='replace')
    
    # Generate unified diff
    diff_lines = list(unified_diff(
        v1_content.splitlines(),
        v2_content.splitlines(),
        fromfile=f"{filepath.name} (v{v1})",
        tofile=f"{filepath.name} (v{v2})",
        lineterm=''
    ))
    
    # Analyze changes
    changes = parse_changes(v1_content, v2_content, file_info['type'])
    summary = generate_summary(changes, file_info['type'], filepath.name)
    
    return {
        "file": filepath.name,
        "v1": v1,
        "v2": v2,
        "v1_timestamp": versions[v1-1]['timestamp'],
        "v2_timestamp": versions[v2-1]['timestamp'],
        "diff": '\n'.join(diff_lines),
        "summary": summary,
        "changes": changes
    }


def get_history(filepath: Path, limit: int = 10) -> Dict:
    """Get version history for a file."""
    index = load_index()
    file_id = get_file_id(filepath)
    
    if file_id not in index['files']:
        return {"error": f"File not tracked: {filepath}"}
    
    file_info = index['files'][file_id]
    versions = file_info['versions'][-limit:]
    
    return {
        "file": filepath.name,
        "path": file_info['path'],
        "type": file_info['type'],
        "total_versions": len(file_info['versions']),
        "created": file_info['created'],
        "updated": file_info['updated'],
        "versions": versions[::-1]  # Most recent first
    }


def get_summary_since(filepath: Path, since: str) -> Dict:
    """Get summary of all changes since a date."""
    index = load_index()
    file_id = get_file_id(filepath)
    
    if file_id not in index['files']:
        return {"error": f"File not tracked: {filepath}"}
    
    file_info = index['files'][file_id]
    
    # Parse date
    try:
        since_date = datetime.fromisoformat(since.replace('Z', '+00:00'))
    except ValueError:
        # Try parsing as relative date
        if since.endswith('d'):
            days = int(since[:-1])
            since_date = datetime.now() - timedelta(days=days)
        elif since.endswith('w'):
            weeks = int(since[:-1])
            since_date = datetime.now() - timedelta(weeks=weeks)
        else:
            return {"error": f"Invalid date format: {since}"}
    
    # Filter versions since date
    versions = []
    for v in file_info['versions']:
        v_date = datetime.fromisoformat(v['timestamp'].replace('Z', '+00:00'))
        if v_date >= since_date:
            versions.append(v)
    
    if not versions:
        return {
            "file": filepath.name,
            "since": since_date.isoformat(),
            "changes": 0,
            "message": "No changes since specified date"
        }
    
    total_added = sum(v.get('lines_added', 0) for v in versions)
    total_removed = sum(v.get('lines_removed', 0) for v in versions)
    
    summaries = [v.get('summary', '') for v in versions if v.get('summary')]
    
    return {
        "file": filepath.name,
        "since": since_date.isoformat(),
        "changes": len(versions),
        "total_lines_added": total_added,
        "total_lines_removed": total_removed,
        "summaries": summaries
    }


def watch_path(path: Path, interval: int = 30):
    """Watch a path for changes and auto-track."""
    print(f"👁️  Watching {path} for changes (checking every {interval}s)")
    print("Press Ctrl+C to stop\n")
    
    tracked_files = {}
    
    def scan_files():
        if path.is_file():
            return [path]
        else:
            files = []
            for pattern in ['*.py', '*.js', '*.ts', '*.md', '*.json', '*.yaml', '*.txt']:
                files.extend(path.glob(f'**/{pattern}'))
            return files
    
    try:
        while True:
            files = scan_files()
            
            for filepath in files:
                if filepath.is_file():
                    current_hash = file_hash(filepath)
                    
                    if filepath not in tracked_files:
                        # New file
                        result = track_file(filepath)
                        tracked_files[filepath] = current_hash
                        print(f"📄 {result.get('status', 'tracked')}: {filepath.name}")
                    
                    elif tracked_files[filepath] != current_hash:
                        # File changed
                        result = track_file(filepath)
                        tracked_files[filepath] = current_hash
                        print(f"\n🔄 {filepath.name} updated!")
                        if result.get('summary'):
                            print(f"   {result['summary'][:100]}...")
            
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopped watching")


def generate_report(days: int = 7) -> Dict:
    """Generate report of all changes in the past N days."""
    history = load_history()
    index = load_index()
    
    since = datetime.now() - timedelta(days=days)
    
    recent_changes = []
    for change in history['changes']:
        change_date = datetime.fromisoformat(change['timestamp'].replace('Z', '+00:00'))
        if change_date >= since:
            recent_changes.append(change)
    
    # Group by file
    by_file = {}
    for change in recent_changes:
        fname = change.get('name', change.get('file', 'unknown'))
        if fname not in by_file:
            by_file[fname] = []
        by_file[fname].append(change)
    
    # Statistics
    total_added = sum(c.get('lines_added', 0) for c in recent_changes)
    total_removed = sum(c.get('lines_removed', 0) for c in recent_changes)
    
    return {
        "period": f"Last {days} days",
        "since": since.isoformat(),
        "total_changes": len(recent_changes),
        "files_modified": len(by_file),
        "total_files_tracked": len(index['files']),
        "lines_added": total_added,
        "lines_removed": total_removed,
        "by_file": {k: len(v) for k, v in by_file.items()},
        "recent_summaries": [c.get('summary', '') for c in recent_changes[-10:]]
    }


def restore_version(filepath: Path, version: int) -> Dict:
    """Restore a file to a previous version."""
    index = load_index()
    file_id = get_file_id(filepath)
    
    if file_id not in index['files']:
        return {"error": f"File not tracked: {filepath}"}
    
    file_info = index['files'][file_id]
    versions = file_info['versions']
    
    if version < 1 or version > len(versions):
        return {"error": f"Invalid version. Available: 1-{len(versions)}"}
    
    version_path = VERSIONS_DIR / f"{file_id}_v{version}.txt"
    if not version_path.exists():
        return {"error": "Version content not found"}
    
    content = version_path.read_text(encoding='utf-8', errors='replace')
    
    # Backup current version first
    track_file(filepath)
    
    # Restore
    filepath.write_text(content, encoding='utf-8')
    
    # Track the restoration
    result = track_file(filepath)
    
    return {
        "status": "restored",
        "file": filepath.name,
        "restored_to_version": version,
        "current_version": result.get('version', 'unknown'),
        "message": f"Restored {filepath.name} to version {version}"
    }


def search_changes(query: str) -> Dict:
    """Search through change summaries."""
    history = load_history()
    
    query_lower = query.lower()
    matches = []
    
    for change in history['changes']:
        summary = change.get('summary', '').lower()
        name = change.get('name', '').lower()
        
        if query_lower in summary or query_lower in name:
            matches.append(change)
    
    return {
        "query": query,
        "matches": len(matches),
        "results": matches[-20:]  # Most recent 20
    }


def get_stats() -> Dict:
    """Get overall tracking statistics."""
    index = load_index()
    history = load_history()
    
    total_files = len(index['files'])
    total_versions = sum(len(f['versions']) for f in index['files'].values())
    total_changes = len(history['changes'])
    
    # Type breakdown
    by_type = {}
    for f in index['files'].values():
        ftype = f.get('type', 'unknown')
        by_type[ftype] = by_type.get(ftype, 0) + 1
    
    # Recent activity
    now = datetime.now()
    recent_24h = sum(1 for c in history['changes'] 
                     if datetime.fromisoformat(c['timestamp'].replace('Z', '+00:00')) > now - timedelta(hours=24))
    recent_7d = sum(1 for c in history['changes']
                    if datetime.fromisoformat(c['timestamp'].replace('Z', '+00:00')) > now - timedelta(days=7))
    
    return {
        "total_files_tracked": total_files,
        "total_versions_stored": total_versions,
        "total_changes_logged": total_changes,
        "by_file_type": by_type,
        "changes_last_24h": recent_24h,
        "changes_last_7d": recent_7d,
        "data_directory": str(DATA_DIR)
    }


def format_output(data: Dict, as_json: bool = False) -> str:
    """Format output for display."""
    if as_json:
        return json.dumps(data, indent=2)
    
    if 'error' in data:
        return f"❌ Error: {data['error']}"
    
    lines = []
    
    if 'status' in data:
        status_icons = {'tracking': '📄', 'updated': '🔄', 'unchanged': '✓', 'restored': '⏪'}
        icon = status_icons.get(data['status'], '•')
        lines.append(f"{icon} {data['status'].upper()}: {data.get('file', data.get('message', ''))}")
        
        if data.get('summary'):
            lines.append(f"\n{data['summary']}")
        
        if data.get('version'):
            lines.append(f"\nVersion: {data['version']}")
    
    elif 'versions' in data:
        lines.append(f"📜 VERSION HISTORY: {data['file']}")
        lines.append(f"   Type: {data['type']} | Total versions: {data['total_versions']}")
        lines.append(f"   Tracking since: {data['created'][:10]}\n")
        
        for v in data['versions']:
            lines.append(f"   v{v['version']} [{v['timestamp'][:16]}]")
            lines.append(f"      +{v.get('lines_added', 0)}/-{v.get('lines_removed', 0)} lines | {v.get('similarity', 0)}% similar")
            if v.get('summary'):
                lines.append(f"      {v['summary'][:80]}...")
            lines.append("")
    
    elif 'diff' in data:
        lines.append(f"📊 DIFF: {data['file']} (v{data['v1']} → v{data['v2']})")
        lines.append(f"\n{data['summary']}\n")
        lines.append("─" * 60)
        lines.append(data['diff'])
    
    elif 'total_changes' in data:
        lines.append(f"📈 CHANGE REPORT: {data['period']}")
        lines.append(f"   Total changes: {data['total_changes']}")
        lines.append(f"   Files modified: {data['files_modified']}")
        lines.append(f"   Lines: +{data['lines_added']}/-{data['lines_removed']}")
        
        if data.get('by_file'):
            lines.append("\n   Changes by file:")
            for fname, count in sorted(data['by_file'].items(), key=lambda x: -x[1])[:10]:
                lines.append(f"      {fname}: {count} changes")
    
    elif 'total_files_tracked' in data:
        lines.append("📊 VERSION TRACKING STATS")
        lines.append(f"   Files tracked: {data['total_files_tracked']}")
        lines.append(f"   Versions stored: {data['total_versions_stored']}")
        lines.append(f"   Total changes: {data['total_changes_logged']}")
        lines.append(f"   Last 24h: {data['changes_last_24h']} changes")
        lines.append(f"   Last 7d: {data['changes_last_7d']} changes")
        
        if data.get('by_file_type'):
            lines.append("\n   By file type:")
            for ftype, count in sorted(data['by_file_type'].items()):
                lines.append(f"      {ftype}: {count}")
    
    elif 'matches' in data:
        lines.append(f"🔍 SEARCH: '{data['query']}' ({data['matches']} matches)")
        for result in data['results'][-10:]:
            lines.append(f"\n   {result.get('name', 'unknown')} v{result.get('version', '?')}")
            lines.append(f"      {result.get('summary', 'No summary')[:80]}")
    
    else:
        return json.dumps(data, indent=2)
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Document Version Summaries - Track file changes with human-readable summaries'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # track command
    track_parser = subparsers.add_parser('track', help='Track a file')
    track_parser.add_argument('file', help='File to track')
    track_parser.add_argument('--name', help='Display name for the file')
    track_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # diff command
    diff_parser = subparsers.add_parser('diff', help='Show diff between versions')
    diff_parser.add_argument('file', help='File to diff')
    diff_parser.add_argument('--v1', type=int, help='First version (default: second-to-last)')
    diff_parser.add_argument('--v2', type=int, help='Second version (default: last)')
    diff_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # history command
    history_parser = subparsers.add_parser('history', help='Show version history')
    history_parser.add_argument('file', help='File to show history for')
    history_parser.add_argument('--limit', type=int, default=10, help='Number of versions to show')
    history_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # summary command
    summary_parser = subparsers.add_parser('summary', help='Summarize changes since date')
    summary_parser.add_argument('file', help='File to summarize')
    summary_parser.add_argument('--since', default='7d', help='Date or relative (7d, 2w)')
    summary_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # watch command
    watch_parser = subparsers.add_parser('watch', help='Watch path for changes')
    watch_parser.add_argument('path', help='File or directory to watch')
    watch_parser.add_argument('--interval', type=int, default=30, help='Check interval in seconds')
    
    # report command
    report_parser = subparsers.add_parser('report', help='Generate change report')
    report_parser.add_argument('--days', type=int, default=7, help='Days to include')
    report_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # restore command
    restore_parser = subparsers.add_parser('restore', help='Restore file to previous version')
    restore_parser.add_argument('file', help='File to restore')
    restore_parser.add_argument('--version', type=int, required=True, help='Version to restore')
    restore_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # search command
    search_parser = subparsers.add_parser('search', help='Search change summaries')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # stats command
    stats_parser = subparsers.add_parser('stats', help='Show tracking statistics')
    stats_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    ensure_data_dirs()
    
    result = {}
    as_json = getattr(args, 'json', False)
    
    if args.command == 'track':
        result = track_file(Path(args.file), args.name)
    
    elif args.command == 'diff':
        result = get_diff(Path(args.file), args.v1, args.v2)
    
    elif args.command == 'history':
        result = get_history(Path(args.file), args.limit)
    
    elif args.command == 'summary':
        result = get_summary_since(Path(args.file), args.since)
    
    elif args.command == 'watch':
        watch_path(Path(args.path), args.interval)
        return
    
    elif args.command == 'report':
        result = generate_report(args.days)
    
    elif args.command == 'restore':
        result = restore_version(Path(args.file), args.version)
    
    elif args.command == 'search':
        result = search_changes(args.query)
    
    elif args.command == 'stats':
        result = get_stats()
    
    print(format_output(result, as_json))


if __name__ == '__main__':
    main()
