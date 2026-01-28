# Context-Aware Clipboard Manager

Semantic clipboard history with natural language recall. Track, search, and organize everything you copy.

## Features

- **Smart Content Detection**: Auto-detects URLs, code, emails, file paths, commands
- **Automatic Tagging**: Tags clips based on content keywords
- **Keyword Extraction**: Extracts meaningful keywords for search
- **Natural Search**: Find clips by content, type, tags, or keywords
- **Pin Important Clips**: Keep frequently used clips accessible
- **Duplicate Detection**: Optionally merge duplicate copies
- **Type Filtering**: Filter by code, URLs, emails, etc.

## Quick Start

```bash
# Capture current clipboard
python clipboard_manager.py capture

# Add text with tags
python clipboard_manager.py add "SELECT * FROM users WHERE active = true" --tags "work,database"

# Search clips
python clipboard_manager.py search "function"
python clipboard_manager.py search --type code_python
python clipboard_manager.py search --tags "work"

# View recent clips
python clipboard_manager.py recent --limit 10

# Recall a clip (copies to clipboard)
python clipboard_manager.py recall abc123def456

# Pin important clips
python clipboard_manager.py pin abc123def456
```

## Commands

### capture
Capture current clipboard content.
```bash
python clipboard_manager.py capture
python clipboard_manager.py capture --tags "meeting,notes"
python clipboard_manager.py capture --text "override text"
```

### add
Manually add text to history.
```bash
python clipboard_manager.py add "some text" --tags "work"
```

### search
Search clipboard history.
```bash
python clipboard_manager.py search "query"
python clipboard_manager.py search --type url
python clipboard_manager.py search --tags "code,work"
python clipboard_manager.py search --days 7 --limit 50
```

### recent
Show recent clips.
```bash
python clipboard_manager.py recent
python clipboard_manager.py recent --limit 20 --json
```

### recall
Recall a clip to clipboard.
```bash
python clipboard_manager.py recall CLIP_ID
python clipboard_manager.py recall CLIP_ID --show
```

### pin
Pin or unpin important clips.
```bash
python clipboard_manager.py pin CLIP_ID
python clipboard_manager.py pin CLIP_ID --unpin
```

### tag
Add or replace tags.
```bash
python clipboard_manager.py tag CLIP_ID --tags "important,work"
python clipboard_manager.py tag CLIP_ID --tags "new,tags" --replace
```

### delete
Delete a clip.
```bash
python clipboard_manager.py delete CLIP_ID
```

### clear
Clear history.
```bash
python clipboard_manager.py clear --force  # Keep pinned
python clipboard_manager.py clear --force --all  # Delete everything
```

### types
List content types.
```bash
python clipboard_manager.py types
```

### stats
View statistics.
```bash
python clipboard_manager.py stats
```

### config
View or update configuration.
```bash
python clipboard_manager.py config
python clipboard_manager.py config --key max_history --value 2000
```

## Content Types

| Type | Description | Examples |
|------|-------------|----------|
| `url` | Web addresses | https://..., www... |
| `email` | Email addresses | user@domain.com |
| `code_python` | Python code | def, class, import |
| `code_javascript` | JavaScript | function, const, => |
| `code_json` | JSON data | {"key": "value"} |
| `code_sql` | SQL queries | SELECT, INSERT |
| `command` | Shell commands | git, npm, pip |
| `file_path` | File paths | C:\..., /home/... |
| `phone` | Phone numbers | 555-123-4567 |
| `date` | Dates | 2025-01-27, 1/27/25 |
| `markdown` | Markdown text | # Headers, **bold** |
| `text` | Plain text | (default) |

## Configuration

| Key | Description | Default |
|-----|-------------|---------|
| `max_history` | Maximum clips to keep | 1000 |
| `retention_days` | Days to retain clips | 30 |
| `auto_categorize` | Auto-detect content type | true |
| `track_duplicates` | Keep duplicate copies | false |
| `snippet_max_length` | Preview length | 200 |
| `auto_tag_keywords` | Keywords for auto-tagging | {...} |

## Integration Ideas

### Hotkey Integration
Use AutoHotkey or similar to trigger capture:
```autohotkey
; Ctrl+Shift+C to capture
^+c::
    Run, python clipboard_manager.py capture
return
```

### Background Watcher
Poll clipboard periodically:
```bash
# Simple watcher script
while true; do
    python clipboard_manager.py capture 2>/dev/null
    sleep 5
done
```

### Alfred/Raycast Integration
Create workflows to search and recall clips.

## Data Files

- `data/clipboard_history.json` - Clip history
- `data/tags.json` - Tag definitions
- `data/config.json` - Configuration
- `data/pinned.json` - Pinned clip references

---
Built by PM3 (Backend/Data Builder) | Context-Aware Clipboard v1.0
