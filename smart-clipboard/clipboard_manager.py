#!/usr/bin/env python3
"""
Context-Aware Clipboard Manager
Semantic clipboard history with natural recall.
Built by PM3 (Backend/Data Builder)
"""

import argparse
import json
import os
import re
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
import subprocess

DATA_DIR = Path(__file__).parent / "data"
HISTORY_FILE = DATA_DIR / "clipboard_history.json"
TAGS_FILE = DATA_DIR / "tags.json"
CONFIG_FILE = DATA_DIR / "config.json"
PINS_FILE = DATA_DIR / "pinned.json"


def ensure_data_dir():
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_json(filepath: Path, default=None):
    """Load JSON file or return default."""
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default if default is not None else {}


def save_json(filepath: Path, data):
    """Save data to JSON file."""
    ensure_data_dir()
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)


def get_config() -> Dict:
    """Get configuration with defaults."""
    config = load_json(CONFIG_FILE, {})
    defaults = {
        "max_history": 1000,
        "retention_days": 30,
        "auto_categorize": True,
        "track_duplicates": False,
        "snippet_max_length": 200,
        "auto_tag_keywords": {
            "meeting": ["meeting", "calendar", "schedule", "zoom", "teams"],
            "email": ["@", "email", "subject:", "from:", "to:"],
            "code": ["function", "def ", "class ", "import ", "const ", "var ", "let "],
            "link": ["http://", "https://", "www."]
        }
    }
    for k, v in defaults.items():
        if k not in config:
            config[k] = v
    return config


# Content Type Detection
CONTENT_TYPES = {
    "url": {
        "patterns": [r"https?://\S+", r"www\.\S+"],
        "priority": 10
    },
    "email": {
        "patterns": [r"[\w\.-]+@[\w\.-]+\.\w+"],
        "priority": 9
    },
    "code_python": {
        "patterns": [r"^\s*def \w+\(", r"^\s*class \w+", r"^\s*import \w+", r"^\s*from \w+ import"],
        "priority": 8
    },
    "code_javascript": {
        "patterns": [r"^\s*function\s+\w+\s*\(", r"^\s*const\s+\w+\s*=", r"^\s*let\s+\w+\s*=", r"=>\s*{"],
        "priority": 8
    },
    "code_json": {
        "patterns": [r'^\s*\{[\s\S]*"[\w]+"\s*:'],
        "priority": 7
    },
    "code_sql": {
        "patterns": [r"^\s*SELECT\s+", r"^\s*INSERT\s+INTO", r"^\s*UPDATE\s+\w+\s+SET", r"^\s*CREATE\s+TABLE"],
        "priority": 8
    },
    "file_path": {
        "patterns": [r"^[A-Za-z]:\\[\w\\\.-]+", r"^/[\w/\.-]+", r"^~/[\w/\.-]+"],
        "priority": 7
    },
    "phone": {
        "patterns": [r"\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"],
        "priority": 6
    },
    "date": {
        "patterns": [r"\d{1,2}/\d{1,2}/\d{2,4}", r"\d{4}-\d{2}-\d{2}"],
        "priority": 5
    },
    "number": {
        "patterns": [r"^\$?[\d,]+\.?\d*$", r"^[\d,]+\.?\d*%$"],
        "priority": 4
    },
    "command": {
        "patterns": [r"^\s*(git|npm|pip|docker|kubectl|yarn|cargo)\s+\w+"],
        "priority": 8
    },
    "markdown": {
        "patterns": [r"^#+\s+", r"^\*\*\w+\*\*", r"^\[[\w\s]+\]\("],
        "priority": 6
    },
    "text": {
        "patterns": [],
        "priority": 1
    }
}


def detect_content_type(content: str) -> Tuple[str, float]:
    """Detect content type and confidence."""
    content = content.strip()
    
    best_type = "text"
    best_priority = 0
    
    for type_name, type_info in CONTENT_TYPES.items():
        for pattern in type_info.get('patterns', []):
            try:
                if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                    if type_info['priority'] > best_priority:
                        best_type = type_name
                        best_priority = type_info['priority']
                    break
            except:
                continue
    
    confidence = best_priority / 10.0
    return best_type, confidence


def extract_keywords(content: str) -> List[str]:
    """Extract meaningful keywords from content."""
    # Remove URLs and emails
    cleaned = re.sub(r'https?://\S+', '', content)
    cleaned = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', cleaned)
    
    # Extract words (alphanumeric, 3+ chars)
    words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9]{2,}\b', cleaned.lower())
    
    # Remove common stop words
    stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 
                  'was', 'one', 'our', 'out', 'has', 'have', 'been', 'from', 'this', 'that',
                  'with', 'they', 'will', 'would', 'there', 'their', 'what', 'about', 'which'}
    
    keywords = [w for w in words if w not in stop_words]
    
    # Return unique keywords, preserve order
    seen = set()
    unique = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)
    
    return unique[:20]  # Max 20 keywords


def auto_tag_content(content: str, config: Dict) -> List[str]:
    """Auto-generate tags based on content."""
    tags = []
    content_lower = content.lower()
    
    for tag, keywords in config.get('auto_tag_keywords', {}).items():
        for kw in keywords:
            if kw in content_lower:
                tags.append(tag)
                break
    
    # Add content type as tag
    content_type, _ = detect_content_type(content)
    if content_type != "text":
        tags.append(content_type)
    
    return list(set(tags))


def generate_clip_id(content: str, timestamp: str) -> str:
    """Generate unique clip ID."""
    data = f"{content[:100]}{timestamp}"
    return hashlib.md5(data.encode()).hexdigest()[:12]


def get_clipboard_content() -> Optional[str]:
    """Get current clipboard content (Windows)."""
    try:
        # Windows PowerShell method
        result = subprocess.run(
            ['powershell', '-command', 'Get-Clipboard'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception as e:
        return None


def set_clipboard_content(content: str) -> bool:
    """Set clipboard content (Windows)."""
    try:
        # Escape for PowerShell
        escaped = content.replace("'", "''")
        result = subprocess.run(
            ['powershell', '-command', f"Set-Clipboard -Value '{escaped}'"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception as e:
        return False


def add_to_history(content: str, source: str = "manual", tags: List[str] = None) -> Dict:
    """Add content to clipboard history."""
    config = get_config()
    history = load_json(HISTORY_FILE, {"clips": []})
    
    timestamp = datetime.now().isoformat()
    content_type, confidence = detect_content_type(content)
    keywords = extract_keywords(content)
    auto_tags = auto_tag_content(content, config) if config.get('auto_categorize') else []
    
    clip = {
        "id": generate_clip_id(content, timestamp),
        "content": content,
        "snippet": content[:config.get('snippet_max_length', 200)],
        "content_type": content_type,
        "type_confidence": confidence,
        "keywords": keywords,
        "tags": list(set((tags or []) + auto_tags)),
        "source": source,
        "created": timestamp,
        "accessed_count": 0,
        "last_accessed": None,
        "pinned": False,
        "char_count": len(content),
        "word_count": len(content.split()),
        "line_count": content.count('\n') + 1
    }
    
    # Check for duplicates
    if not config.get('track_duplicates', False):
        content_hash = hashlib.md5(content.encode()).hexdigest()
        for existing in history['clips']:
            if hashlib.md5(existing['content'].encode()).hexdigest() == content_hash:
                # Update existing clip's timestamp
                existing['last_accessed'] = timestamp
                existing['accessed_count'] = existing.get('accessed_count', 0) + 1
                save_json(HISTORY_FILE, history)
                return existing
    
    history['clips'].insert(0, clip)
    
    # Enforce max history
    max_history = config.get('max_history', 1000)
    # Keep pinned clips
    pinned = [c for c in history['clips'] if c.get('pinned')]
    unpinned = [c for c in history['clips'] if not c.get('pinned')]
    unpinned = unpinned[:max_history - len(pinned)]
    history['clips'] = pinned + unpinned
    
    save_json(HISTORY_FILE, history)
    return clip


def search_history(query: str = None, content_type: str = None, tags: List[str] = None,
                  days: int = None, limit: int = 50) -> List[Dict]:
    """Search clipboard history."""
    history = load_json(HISTORY_FILE, {"clips": []})
    clips = history.get('clips', [])
    
    results = []
    
    cutoff = None
    if days:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    query_lower = query.lower() if query else None
    
    for clip in clips:
        # Time filter
        if cutoff and clip.get('created', '') < cutoff:
            continue
        
        # Content type filter
        if content_type and clip.get('content_type') != content_type:
            continue
        
        # Tags filter
        if tags:
            clip_tags = set(clip.get('tags', []))
            if not any(t in clip_tags for t in tags):
                continue
        
        # Query filter (search content, keywords, snippet)
        if query_lower:
            searchable = (
                clip.get('content', '').lower() +
                ' '.join(clip.get('keywords', [])) +
                ' '.join(clip.get('tags', []))
            )
            if query_lower not in searchable:
                continue
        
        results.append(clip)
    
    # Sort by relevance (pinned first, then by date)
    results.sort(key=lambda x: (not x.get('pinned', False), x.get('created', '')), reverse=True)
    
    return results[:limit]


def get_recent(limit: int = 10) -> List[Dict]:
    """Get recent clips."""
    history = load_json(HISTORY_FILE, {"clips": []})
    clips = history.get('clips', [])
    return clips[:limit]


def get_clip_by_id(clip_id: str) -> Optional[Dict]:
    """Get specific clip by ID."""
    history = load_json(HISTORY_FILE, {"clips": []})
    for clip in history.get('clips', []):
        if clip.get('id') == clip_id:
            return clip
    return None


def recall_clip(clip_id: str) -> Optional[str]:
    """Recall a clip (copy to clipboard and mark as accessed)."""
    history = load_json(HISTORY_FILE, {"clips": []})
    
    for clip in history.get('clips', []):
        if clip.get('id') == clip_id:
            # Update access stats
            clip['accessed_count'] = clip.get('accessed_count', 0) + 1
            clip['last_accessed'] = datetime.now().isoformat()
            save_json(HISTORY_FILE, history)
            
            # Copy to clipboard
            if set_clipboard_content(clip['content']):
                return clip['content']
            return clip['content']  # Return content even if clipboard fails
    
    return None


def pin_clip(clip_id: str, pinned: bool = True) -> bool:
    """Pin or unpin a clip."""
    history = load_json(HISTORY_FILE, {"clips": []})
    
    for clip in history.get('clips', []):
        if clip.get('id') == clip_id:
            clip['pinned'] = pinned
            save_json(HISTORY_FILE, history)
            return True
    return False


def tag_clip(clip_id: str, tags: List[str], replace: bool = False) -> bool:
    """Add or replace tags on a clip."""
    history = load_json(HISTORY_FILE, {"clips": []})
    
    for clip in history.get('clips', []):
        if clip.get('id') == clip_id:
            if replace:
                clip['tags'] = tags
            else:
                clip['tags'] = list(set(clip.get('tags', []) + tags))
            save_json(HISTORY_FILE, history)
            return True
    return False


def delete_clip(clip_id: str) -> bool:
    """Delete a clip from history."""
    history = load_json(HISTORY_FILE, {"clips": []})
    original_count = len(history.get('clips', []))
    history['clips'] = [c for c in history.get('clips', []) if c.get('id') != clip_id]
    
    if len(history['clips']) < original_count:
        save_json(HISTORY_FILE, history)
        return True
    return False


def clear_history(keep_pinned: bool = True) -> int:
    """Clear clipboard history."""
    history = load_json(HISTORY_FILE, {"clips": []})
    original_count = len(history.get('clips', []))
    
    if keep_pinned:
        history['clips'] = [c for c in history.get('clips', []) if c.get('pinned')]
    else:
        history['clips'] = []
    
    save_json(HISTORY_FILE, history)
    return original_count - len(history['clips'])


# ============ CLI Commands ============

def cmd_capture(args):
    """Capture current clipboard content."""
    if args.text:
        content = args.text
    else:
        content = get_clipboard_content()
        if not content:
            print("Clipboard is empty or could not be read")
            return
    
    tags = args.tags.split(',') if args.tags else []
    clip = add_to_history(content, source="capture", tags=tags)
    
    if args.json:
        print(json.dumps(clip, indent=2))
    else:
        print(f"Captured clip: {clip['id']}")
        print(f"  Type: {clip['content_type']}")
        print(f"  Tags: {', '.join(clip['tags']) or 'none'}")
        print(f"  Length: {clip['char_count']} chars, {clip['word_count']} words")


def cmd_add(args):
    """Add text to clipboard history."""
    tags = args.tags.split(',') if args.tags else []
    clip = add_to_history(args.text, source="manual", tags=tags)
    
    if args.json:
        print(json.dumps(clip, indent=2))
    else:
        print(f"Added clip: {clip['id']}")
        print(f"  Type: {clip['content_type']}")
        print(f"  Snippet: {clip['snippet'][:50]}...")


def cmd_search(args):
    """Search clipboard history."""
    tags = args.tags.split(',') if args.tags else None
    results = search_history(
        query=args.query,
        content_type=args.type,
        tags=tags,
        days=args.days,
        limit=args.limit or 20
    )
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        if not results:
            print("No clips found")
            return
        
        print(f"\nSearch Results ({len(results)} clips)")
        print("=" * 60)
        for clip in results:
            pinned = "[PIN] " if clip.get('pinned') else ""
            tags_str = f" [{', '.join(clip.get('tags', []))}]" if clip.get('tags') else ""
            print(f"\n{pinned}{clip['id']} | {clip['content_type']}{tags_str}")
            print(f"  {clip['snippet'][:80]}{'...' if len(clip.get('content', '')) > 80 else ''}")
            print(f"  {clip['created'][:16]} | {clip['char_count']} chars")


def cmd_recent(args):
    """Show recent clips."""
    clips = get_recent(args.limit or 10)
    
    if args.json:
        print(json.dumps(clips, indent=2))
    else:
        if not clips:
            print("No clips in history")
            return
        
        print(f"\nRecent Clips ({len(clips)})")
        print("=" * 60)
        for i, clip in enumerate(clips, 1):
            pinned = "[PIN] " if clip.get('pinned') else ""
            print(f"\n{i}. {pinned}{clip['id']} | {clip['content_type']}")
            print(f"   {clip['snippet'][:60]}...")
            print(f"   {clip['created'][:16]}")


def cmd_recall(args):
    """Recall a clip to clipboard."""
    content = recall_clip(args.clip_id)
    
    if content:
        print(f"Recalled clip {args.clip_id}")
        if args.show:
            print("-" * 40)
            print(content)
    else:
        print(f"Clip {args.clip_id} not found")


def cmd_pin(args):
    """Pin or unpin a clip."""
    success = pin_clip(args.clip_id, not args.unpin)
    action = "Unpinned" if args.unpin else "Pinned"
    
    if success:
        print(f"{action} clip {args.clip_id}")
    else:
        print(f"Clip {args.clip_id} not found")


def cmd_tag(args):
    """Add tags to a clip."""
    tags = args.tags.split(',')
    success = tag_clip(args.clip_id, tags, args.replace)
    
    if success:
        action = "Replaced tags on" if args.replace else "Tagged"
        print(f"{action} clip {args.clip_id}: {', '.join(tags)}")
    else:
        print(f"Clip {args.clip_id} not found")


def cmd_delete(args):
    """Delete a clip."""
    if delete_clip(args.clip_id):
        print(f"Deleted clip {args.clip_id}")
    else:
        print(f"Clip {args.clip_id} not found")


def cmd_clear(args):
    """Clear history."""
    if not args.force:
        print("This will clear clipboard history. Use --force to confirm.")
        return
    
    deleted = clear_history(keep_pinned=not args.all)
    print(f"Cleared {deleted} clips" + (" (kept pinned)" if not args.all else ""))


def cmd_types(args):
    """List content types."""
    if args.json:
        print(json.dumps(CONTENT_TYPES, indent=2))
    else:
        print("\nContent Types")
        print("=" * 40)
        for name, info in sorted(CONTENT_TYPES.items(), key=lambda x: -x[1]['priority']):
            print(f"  {name}: priority {info['priority']}")


def cmd_stats(args):
    """Show statistics."""
    history = load_json(HISTORY_FILE, {"clips": []})
    clips = history.get('clips', [])
    config = get_config()
    
    # Type distribution
    by_type = defaultdict(int)
    for clip in clips:
        by_type[clip.get('content_type', 'text')] += 1
    
    # Tag distribution
    by_tag = defaultdict(int)
    for clip in clips:
        for tag in clip.get('tags', []):
            by_tag[tag] += 1
    
    pinned_count = sum(1 for c in clips if c.get('pinned'))
    total_chars = sum(c.get('char_count', 0) for c in clips)
    
    print("\nClipboard Statistics")
    print("=" * 50)
    print(f"Total clips: {len(clips)}")
    print(f"Pinned clips: {pinned_count}")
    print(f"Total characters: {total_chars:,}")
    print(f"Max history: {config.get('max_history')}")
    
    if by_type:
        print("\nBy content type:")
        for t, count in sorted(by_type.items(), key=lambda x: -x[1])[:5]:
            print(f"  {t}: {count}")
    
    if by_tag:
        print("\nTop tags:")
        for tag, count in sorted(by_tag.items(), key=lambda x: -x[1])[:5]:
            print(f"  {tag}: {count}")


def cmd_config(args):
    """View or update config."""
    config = get_config()
    
    if args.key and args.value:
        try:
            value = json.loads(args.value)
        except:
            value = args.value
        config[args.key] = value
        save_json(CONFIG_FILE, config)
        print(f"Set {args.key} = {value}")
        return
    
    if args.json:
        print(json.dumps(config, indent=2))
    else:
        print("\nConfiguration")
        print("=" * 50)
        for k, v in config.items():
            if isinstance(v, dict):
                print(f"{k}: <dict with {len(v)} keys>")
            elif isinstance(v, list):
                print(f"{k}: [{', '.join(str(x) for x in v[:3])}...]")
            else:
                print(f"{k}: {v}")


def main():
    parser = argparse.ArgumentParser(
        description="Context-Aware Clipboard - Semantic clipboard history with natural recall",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s capture                       Capture current clipboard
  %(prog)s capture --tags "work,code"    Capture with tags
  %(prog)s add "some text" --tags "note" Add text manually
  %(prog)s search "function"             Search clips
  %(prog)s search --type code_python     Search by type
  %(prog)s recent --limit 5              Show recent clips
  %(prog)s recall abc123                 Recall clip to clipboard
  %(prog)s pin abc123                    Pin important clip
  %(prog)s tag abc123 --tags "important" Add tags
  %(prog)s stats                         View statistics
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # capture
    p_cap = subparsers.add_parser('capture', help='Capture current clipboard')
    p_cap.add_argument('--text', '-t', help='Text to capture (instead of clipboard)')
    p_cap.add_argument('--tags', help='Comma-separated tags')
    p_cap.add_argument('--json', action='store_true', help='JSON output')
    
    # add
    p_add = subparsers.add_parser('add', help='Add text to history')
    p_add.add_argument('text', help='Text to add')
    p_add.add_argument('--tags', help='Comma-separated tags')
    p_add.add_argument('--json', action='store_true', help='JSON output')
    
    # search
    p_search = subparsers.add_parser('search', help='Search history')
    p_search.add_argument('query', nargs='?', help='Search query')
    p_search.add_argument('--type', '-t', help='Filter by content type')
    p_search.add_argument('--tags', help='Filter by tags (comma-separated)')
    p_search.add_argument('--days', '-d', type=int, help='Limit to N days')
    p_search.add_argument('--limit', '-l', type=int, help='Max results')
    p_search.add_argument('--json', action='store_true', help='JSON output')
    
    # recent
    p_recent = subparsers.add_parser('recent', help='Show recent clips')
    p_recent.add_argument('--limit', '-l', type=int, default=10, help='Number of clips')
    p_recent.add_argument('--json', action='store_true', help='JSON output')
    
    # recall
    p_recall = subparsers.add_parser('recall', help='Recall clip to clipboard')
    p_recall.add_argument('clip_id', help='Clip ID')
    p_recall.add_argument('--show', '-s', action='store_true', help='Show content')
    
    # pin
    p_pin = subparsers.add_parser('pin', help='Pin/unpin a clip')
    p_pin.add_argument('clip_id', help='Clip ID')
    p_pin.add_argument('--unpin', '-u', action='store_true', help='Unpin instead')
    
    # tag
    p_tag = subparsers.add_parser('tag', help='Add tags to clip')
    p_tag.add_argument('clip_id', help='Clip ID')
    p_tag.add_argument('--tags', required=True, help='Comma-separated tags')
    p_tag.add_argument('--replace', '-r', action='store_true', help='Replace all tags')
    
    # delete
    p_del = subparsers.add_parser('delete', help='Delete a clip')
    p_del.add_argument('clip_id', help='Clip ID')
    
    # clear
    p_clear = subparsers.add_parser('clear', help='Clear history')
    p_clear.add_argument('--force', '-f', action='store_true', help='Confirm clear')
    p_clear.add_argument('--all', '-a', action='store_true', help='Include pinned')
    
    # types
    p_types = subparsers.add_parser('types', help='List content types')
    p_types.add_argument('--json', action='store_true', help='JSON output')
    
    # stats
    p_stats = subparsers.add_parser('stats', help='Show statistics')
    
    # config
    p_config = subparsers.add_parser('config', help='View/update config')
    p_config.add_argument('--key', help='Config key')
    p_config.add_argument('--value', help='Config value')
    p_config.add_argument('--json', action='store_true', help='JSON output')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    commands = {
        'capture': cmd_capture,
        'add': cmd_add,
        'search': cmd_search,
        'recent': cmd_recent,
        'recall': cmd_recall,
        'pin': cmd_pin,
        'tag': cmd_tag,
        'delete': cmd_delete,
        'clear': cmd_clear,
        'types': cmd_types,
        'stats': cmd_stats,
        'config': cmd_config
    }
    
    commands[args.command](args)


if __name__ == '__main__':
    main()
