#!/usr/bin/env python3
"""
Automated Changelog Writer - Generate changelogs from git commits.

Parse commits (supports Conventional Commits), categorize changes, and
generate formatted changelogs in Markdown or Keep a Changelog format.

Usage:
    python changelog_gen.py generate [--since <tag/date>] [--until <tag/date>]
    python changelog_gen.py preview [--commits <n>]
    python changelog_gen.py version <version> [--date <date>]
    python changelog_gen.py init [--format <keep|simple>]
    python changelog_gen.py validate
    python changelog_gen.py stats [--since <date>]
    python changelog_gen.py unreleased
    python changelog_gen.py release <version>
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


# Configuration
CONFIG_FILE = Path("changelog.config.json")
CHANGELOG_FILE = Path("CHANGELOG.md")
DATA_DIR = Path(__file__).parent / "data"


# Conventional Commit patterns
COMMIT_TYPES = {
    'feat': {'label': '✨ Features', 'emoji': '✨', 'priority': 1},
    'fix': {'label': '🐛 Bug Fixes', 'emoji': '🐛', 'priority': 2},
    'perf': {'label': '⚡ Performance', 'emoji': '⚡', 'priority': 3},
    'refactor': {'label': '♻️ Refactoring', 'emoji': '♻️', 'priority': 4},
    'docs': {'label': '📚 Documentation', 'emoji': '📚', 'priority': 5},
    'style': {'label': '💄 Styling', 'emoji': '💄', 'priority': 6},
    'test': {'label': '✅ Tests', 'emoji': '✅', 'priority': 7},
    'build': {'label': '📦 Build', 'emoji': '📦', 'priority': 8},
    'ci': {'label': '👷 CI/CD', 'emoji': '👷', 'priority': 9},
    'chore': {'label': '🔧 Chores', 'emoji': '🔧', 'priority': 10},
    'revert': {'label': '⏪ Reverts', 'emoji': '⏪', 'priority': 11},
    'security': {'label': '🔒 Security', 'emoji': '🔒', 'priority': 0},
    'deps': {'label': '📌 Dependencies', 'emoji': '📌', 'priority': 12},
    'breaking': {'label': '💥 Breaking Changes', 'emoji': '💥', 'priority': -1},
}


@dataclass
class Commit:
    """Parsed commit information."""
    hash: str
    short_hash: str
    type: str
    scope: Optional[str]
    subject: str
    body: str
    author: str
    date: str
    breaking: bool = False
    closes: List[str] = field(default_factory=list)
    raw_message: str = ""


@dataclass
class ChangelogEntry:
    """A changelog section/version entry."""
    version: str
    date: str
    commits: List[Commit]
    description: str = ""


def ensure_data_dir():
    """Create data directory if needed."""
    DATA_DIR.mkdir(exist_ok=True)


def load_config() -> Dict:
    """Load changelog configuration."""
    default_config = {
        "format": "keep",  # keep | simple
        "include_commits": True,
        "include_authors": False,
        "include_links": True,
        "repo_url": "",
        "types": list(COMMIT_TYPES.keys()),
        "scopes": [],
        "header": "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\nThe format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),\nand this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n",
        "unreleased_label": "Unreleased"
    }
    
    if CONFIG_FILE.exists():
        try:
            user_config = json.loads(CONFIG_FILE.read_text())
            default_config.update(user_config)
        except json.JSONDecodeError:
            pass
    
    return default_config


def save_config(config: Dict):
    """Save configuration."""
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def run_git(args: List[str]) -> Tuple[bool, str]:
    """Run a git command and return success status and output."""
    try:
        result = subprocess.run(
            ['git'] + args,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, ""


def get_git_tags() -> List[str]:
    """Get all git tags sorted by version."""
    success, output = run_git(['tag', '--sort=-v:refname'])
    if success and output:
        return output.split('\n')
    return []


def get_commits(since: Optional[str] = None, until: Optional[str] = None, limit: int = 100) -> List[Dict]:
    """Get commits from git log."""
    # Custom format: hash|short|author|date|subject|body
    format_str = '%H|%h|%an|%ai|%s|%b%x00'
    
    args = ['log', f'--format={format_str}', f'-n{limit}']
    
    if since and until:
        args.append(f'{since}..{until}')
    elif since:
        args.append(f'{since}..HEAD')
    elif until:
        args.append(until)
    
    success, output = run_git(args)
    
    if not success:
        return []
    
    commits = []
    for entry in output.split('\x00'):
        entry = entry.strip()
        if not entry:
            continue
        
        parts = entry.split('|', 5)
        if len(parts) >= 5:
            commits.append({
                'hash': parts[0],
                'short_hash': parts[1],
                'author': parts[2],
                'date': parts[3][:10],  # Just the date part
                'subject': parts[4],
                'body': parts[5] if len(parts) > 5 else ''
            })
    
    return commits


def parse_commit_message(message: str) -> Tuple[str, Optional[str], str, bool]:
    """Parse a commit message using Conventional Commits format.
    
    Returns: (type, scope, subject, is_breaking)
    """
    # Pattern: type(scope)!: subject or type!: subject or type(scope): subject or type: subject
    pattern = r'^(\w+)(?:\(([^)]+)\))?(!)?:\s*(.+)$'
    match = re.match(pattern, message.strip())
    
    if match:
        commit_type = match.group(1).lower()
        scope = match.group(2)
        breaking = bool(match.group(3))
        subject = match.group(4)
        
        # Normalize some types
        type_map = {
            'feature': 'feat',
            'bug': 'fix',
            'bugfix': 'fix',
            'hotfix': 'fix',
            'doc': 'docs',
            'testing': 'test',
            'tests': 'test',
            'performance': 'perf',
            'dependency': 'deps',
            'dependencies': 'deps',
        }
        commit_type = type_map.get(commit_type, commit_type)
        
        return commit_type, scope, subject, breaking
    
    # Fallback: try to infer type from keywords
    message_lower = message.lower()
    if message_lower.startswith(('add', 'new', 'create', 'implement')):
        return 'feat', None, message, False
    elif message_lower.startswith(('fix', 'bug', 'patch', 'resolve')):
        return 'fix', None, message, False
    elif message_lower.startswith(('doc', 'readme', 'comment')):
        return 'docs', None, message, False
    elif message_lower.startswith(('refactor', 'clean', 'reorganize')):
        return 'refactor', None, message, False
    elif message_lower.startswith(('test', 'spec')):
        return 'test', None, message, False
    elif message_lower.startswith(('update', 'upgrade', 'bump') and 'depend' in message_lower):
        return 'deps', None, message, False
    
    return 'chore', None, message, False


def parse_commit(raw: Dict) -> Commit:
    """Parse a raw commit dict into a Commit object."""
    commit_type, scope, subject, breaking = parse_commit_message(raw['subject'])
    
    # Check for BREAKING CHANGE in body
    body = raw.get('body', '')
    if 'BREAKING CHANGE' in body or 'BREAKING-CHANGE' in body:
        breaking = True
    
    # Extract issue/PR references
    closes = []
    closes_pattern = r'(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*#(\d+)'
    closes.extend(re.findall(closes_pattern, raw['subject'], re.IGNORECASE))
    closes.extend(re.findall(closes_pattern, body, re.IGNORECASE))
    
    return Commit(
        hash=raw['hash'],
        short_hash=raw['short_hash'],
        type=commit_type,
        scope=scope,
        subject=subject,
        body=body,
        author=raw['author'],
        date=raw['date'],
        breaking=breaking,
        closes=closes,
        raw_message=raw['subject']
    )


def categorize_commits(commits: List[Commit]) -> Dict[str, List[Commit]]:
    """Group commits by type."""
    categories = defaultdict(list)
    
    for commit in commits:
        if commit.breaking:
            categories['breaking'].append(commit)
        categories[commit.type].append(commit)
    
    return dict(categories)


def generate_changelog_section(
    commits: List[Commit],
    version: str,
    date_str: str,
    config: Dict
) -> str:
    """Generate a changelog section for a version."""
    lines = []
    
    # Version header
    if version.lower() == 'unreleased':
        lines.append(f"\n## [{config.get('unreleased_label', 'Unreleased')}]\n")
    else:
        lines.append(f"\n## [{version}] - {date_str}\n")
    
    # Categorize commits
    categories = categorize_commits(commits)
    
    # Sort categories by priority
    sorted_types = sorted(
        categories.keys(),
        key=lambda t: COMMIT_TYPES.get(t, {}).get('priority', 99)
    )
    
    for commit_type in sorted_types:
        type_commits = categories[commit_type]
        if not type_commits:
            continue
        
        type_info = COMMIT_TYPES.get(commit_type, {'label': commit_type.title(), 'emoji': '•'})
        lines.append(f"\n### {type_info['label']}\n")
        
        for commit in type_commits:
            # Build commit line
            line = f"- {commit.subject}"
            
            if commit.scope:
                line = f"- **{commit.scope}**: {commit.subject}"
            
            # Add issue references
            if commit.closes and config.get('include_links'):
                refs = ', '.join(f"#{ref}" for ref in commit.closes)
                line += f" ({refs})"
            
            # Add commit hash
            if config.get('include_commits'):
                if config.get('repo_url'):
                    line += f" ([{commit.short_hash}]({config['repo_url']}/commit/{commit.hash}))"
                else:
                    line += f" ({commit.short_hash})"
            
            # Add author
            if config.get('include_authors'):
                line += f" - @{commit.author}"
            
            lines.append(line)
    
    return '\n'.join(lines)


def generate_changelog(
    since: Optional[str] = None,
    until: Optional[str] = None,
    version: str = "Unreleased",
    date_str: Optional[str] = None
) -> str:
    """Generate changelog content."""
    config = load_config()
    
    # Get commits
    raw_commits = get_commits(since=since, until=until)
    
    if not raw_commits:
        return f"No commits found{' since ' + since if since else ''}"
    
    # Parse commits
    commits = [parse_commit(c) for c in raw_commits]
    
    # Filter by configured types
    allowed_types = set(config.get('types', COMMIT_TYPES.keys()))
    commits = [c for c in commits if c.type in allowed_types or c.breaking]
    
    if not commits:
        return "No relevant commits found (all filtered out by type)"
    
    # Use today if no date
    if not date_str:
        date_str = date.today().isoformat()
    
    # Generate section
    section = generate_changelog_section(commits, version, date_str, config)
    
    return section


def get_unreleased_commits() -> List[Commit]:
    """Get commits since the last tag."""
    tags = get_git_tags()
    
    if tags:
        raw_commits = get_commits(since=tags[0])
    else:
        raw_commits = get_commits()
    
    return [parse_commit(c) for c in raw_commits]


def preview_commits(limit: int = 20) -> Dict:
    """Preview recent commits and their parsed types."""
    raw_commits = get_commits(limit=limit)
    commits = [parse_commit(c) for c in raw_commits]
    
    return {
        "total": len(commits),
        "commits": [
            {
                "hash": c.short_hash,
                "type": c.type,
                "scope": c.scope,
                "subject": c.subject,
                "breaking": c.breaking,
                "date": c.date
            }
            for c in commits
        ]
    }


def init_changelog(format_type: str = "keep") -> Dict:
    """Initialize a new changelog file."""
    config = load_config()
    config['format'] = format_type
    
    if CHANGELOG_FILE.exists():
        return {"error": "CHANGELOG.md already exists. Delete it first or use 'generate'."}
    
    # Create initial changelog
    content = config['header']
    content += "\n## [Unreleased]\n\n"
    content += "### Added\n- Initial release\n"
    
    CHANGELOG_FILE.write_text(content)
    save_config(config)
    
    return {
        "status": "created",
        "file": str(CHANGELOG_FILE),
        "format": format_type
    }


def validate_commits(limit: int = 50) -> Dict:
    """Validate that commits follow Conventional Commits format."""
    raw_commits = get_commits(limit=limit)
    
    valid = []
    invalid = []
    
    for raw in raw_commits:
        commit_type, scope, subject, breaking = parse_commit_message(raw['subject'])
        
        # Check if type was properly parsed (not fallback)
        pattern = r'^(\w+)(?:\(([^)]+)\))?(!)?:\s*(.+)$'
        is_conventional = bool(re.match(pattern, raw['subject'].strip()))
        
        entry = {
            "hash": raw['short_hash'],
            "message": raw['subject'][:60],
            "parsed_type": commit_type,
            "conventional": is_conventional
        }
        
        if is_conventional:
            valid.append(entry)
        else:
            invalid.append(entry)
    
    return {
        "total": len(raw_commits),
        "valid": len(valid),
        "invalid": len(invalid),
        "compliance": round(len(valid) / len(raw_commits) * 100, 1) if raw_commits else 0,
        "invalid_commits": invalid[:10]  # Show first 10 invalid
    }


def get_stats(since: Optional[str] = None) -> Dict:
    """Get commit statistics."""
    raw_commits = get_commits(since=since, limit=500)
    commits = [parse_commit(c) for c in raw_commits]
    
    # Count by type
    by_type = defaultdict(int)
    for c in commits:
        by_type[c.type] += 1
    
    # Count by author
    by_author = defaultdict(int)
    for c in commits:
        by_author[c.author] += 1
    
    # Count breaking changes
    breaking = sum(1 for c in commits if c.breaking)
    
    # Count by scope
    by_scope = defaultdict(int)
    for c in commits:
        if c.scope:
            by_scope[c.scope] += 1
    
    return {
        "total_commits": len(commits),
        "since": since or "all time",
        "by_type": dict(sorted(by_type.items(), key=lambda x: -x[1])),
        "by_author": dict(sorted(by_author.items(), key=lambda x: -x[1])[:10]),
        "by_scope": dict(sorted(by_scope.items(), key=lambda x: -x[1])[:10]),
        "breaking_changes": breaking,
        "features": by_type.get('feat', 0),
        "fixes": by_type.get('fix', 0)
    }


def release_version(version: str, date_str: Optional[str] = None) -> Dict:
    """Create a new version release in the changelog."""
    if not date_str:
        date_str = date.today().isoformat()
    
    # Get unreleased commits
    commits = get_unreleased_commits()
    
    if not commits:
        return {"error": "No unreleased commits found"}
    
    config = load_config()
    
    # Generate the new section
    section = generate_changelog_section(commits, version, date_str, config)
    
    # Read existing changelog
    if CHANGELOG_FILE.exists():
        existing = CHANGELOG_FILE.read_text()
        
        # Find the Unreleased section and replace/insert
        unreleased_pattern = r'\n## \[Unreleased\].*?(?=\n## \[|$)'
        
        if re.search(unreleased_pattern, existing, re.DOTALL):
            # Replace unreleased with new version + empty unreleased
            new_unreleased = f"\n## [{config.get('unreleased_label', 'Unreleased')}]\n"
            new_content = re.sub(
                unreleased_pattern,
                new_unreleased + section,
                existing,
                count=1,
                flags=re.DOTALL
            )
        else:
            # Insert after header
            header_end = existing.find('\n## ')
            if header_end == -1:
                new_content = existing + section
            else:
                new_content = existing[:header_end] + section + existing[header_end:]
    else:
        # Create new changelog
        new_content = config['header'] + section
    
    CHANGELOG_FILE.write_text(new_content)
    
    return {
        "status": "released",
        "version": version,
        "date": date_str,
        "commits": len(commits),
        "file": str(CHANGELOG_FILE)
    }


def format_output(data: Any, as_json: bool = False) -> str:
    """Format output for display."""
    if as_json:
        return json.dumps(data, indent=2)
    
    if isinstance(data, str):
        return data
    
    if 'error' in data:
        return f"❌ Error: {data['error']}"
    
    lines = []
    
    if 'commits' in data and 'total' in data:
        # Preview output
        lines.append(f"📋 COMMIT PREVIEW ({data['total']} commits)")
        for c in data['commits']:
            breaking = '💥' if c['breaking'] else ''
            scope = f"({c['scope']})" if c['scope'] else ''
            lines.append(f"   {c['hash']} {c['type']}{scope}: {c['subject'][:50]} {breaking}")
    
    elif 'total_commits' in data:
        # Stats output
        lines.append(f"📊 COMMIT STATISTICS ({data['since']})")
        lines.append(f"   Total commits: {data['total_commits']}")
        lines.append(f"   Features: {data['features']}")
        lines.append(f"   Bug fixes: {data['fixes']}")
        lines.append(f"   Breaking changes: {data['breaking_changes']}")
        
        if data['by_type']:
            lines.append("\n   By type:")
            for ctype, count in data['by_type'].items():
                emoji = COMMIT_TYPES.get(ctype, {}).get('emoji', '•')
                lines.append(f"      {emoji} {ctype}: {count}")
        
        if data['by_author']:
            lines.append("\n   Top contributors:")
            for author, count in list(data['by_author'].items())[:5]:
                lines.append(f"      👤 {author}: {count}")
    
    elif 'compliance' in data:
        # Validation output
        lines.append(f"✅ COMMIT VALIDATION")
        lines.append(f"   Total: {data['total']}")
        lines.append(f"   Valid: {data['valid']} ({data['compliance']}%)")
        lines.append(f"   Invalid: {data['invalid']}")
        
        if data['invalid_commits']:
            lines.append("\n   Non-conventional commits:")
            for c in data['invalid_commits'][:5]:
                lines.append(f"      ⚠️ {c['hash']}: {c['message']}")
    
    elif 'status' in data:
        if data['status'] == 'created':
            lines.append(f"📝 CHANGELOG CREATED: {data['file']}")
            lines.append(f"   Format: {data['format']}")
        elif data['status'] == 'released':
            lines.append(f"🚀 VERSION RELEASED: {data['version']}")
            lines.append(f"   Date: {data['date']}")
            lines.append(f"   Commits: {data['commits']}")
            lines.append(f"   File: {data['file']}")
    
    else:
        return json.dumps(data, indent=2)
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Automated Changelog Writer - Generate changelogs from git commits'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # generate command
    gen_parser = subparsers.add_parser('generate', help='Generate changelog content')
    gen_parser.add_argument('--since', help='Start tag or date')
    gen_parser.add_argument('--until', help='End tag or date')
    gen_parser.add_argument('--version', default='Unreleased', help='Version label')
    gen_parser.add_argument('--date', help='Release date (YYYY-MM-DD)')
    gen_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # preview command
    preview_parser = subparsers.add_parser('preview', help='Preview parsed commits')
    preview_parser.add_argument('--commits', '-n', type=int, default=20, help='Number of commits')
    preview_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # version command (alias for generate with version)
    version_parser = subparsers.add_parser('version', help='Generate changelog for specific version')
    version_parser.add_argument('version', help='Version number (e.g., 1.0.0)')
    version_parser.add_argument('--date', help='Release date')
    version_parser.add_argument('--since', help='Start tag')
    
    # init command
    init_parser = subparsers.add_parser('init', help='Initialize changelog')
    init_parser.add_argument('--format', choices=['keep', 'simple'], default='keep')
    init_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # validate command
    validate_parser = subparsers.add_parser('validate', help='Validate commit format')
    validate_parser.add_argument('--commits', '-n', type=int, default=50, help='Commits to check')
    validate_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # stats command
    stats_parser = subparsers.add_parser('stats', help='Show commit statistics')
    stats_parser.add_argument('--since', help='Since tag or date')
    stats_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # unreleased command
    unreleased_parser = subparsers.add_parser('unreleased', help='Show unreleased changes')
    unreleased_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # release command
    release_parser = subparsers.add_parser('release', help='Create new version release')
    release_parser.add_argument('version', help='Version number')
    release_parser.add_argument('--date', help='Release date')
    release_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    ensure_data_dir()
    
    result = None
    as_json = getattr(args, 'json', False)
    
    if args.command == 'generate':
        result = generate_changelog(
            since=args.since,
            until=args.until,
            version=args.version,
            date_str=args.date
        )
    
    elif args.command == 'preview':
        result = preview_commits(args.commits)
    
    elif args.command == 'version':
        result = generate_changelog(
            since=args.since,
            version=args.version,
            date_str=args.date
        )
    
    elif args.command == 'init':
        result = init_changelog(args.format)
    
    elif args.command == 'validate':
        result = validate_commits(args.commits)
    
    elif args.command == 'stats':
        result = get_stats(args.since)
    
    elif args.command == 'unreleased':
        commits = get_unreleased_commits()
        if commits:
            result = generate_changelog(version="Unreleased")
        else:
            result = "No unreleased commits found"
    
    elif args.command == 'release':
        result = release_version(args.version, args.date)
    
    print(format_output(result, as_json))


if __name__ == '__main__':
    main()
