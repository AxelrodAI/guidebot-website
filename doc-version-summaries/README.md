# Document Version Summaries

Auto-generate human-readable diff summaries when files change. Track document versions with intelligent analysis that explains *what* changed and *why* it matters.

## Features

- **Smart Version Tracking** - Track any text file with automatic content hashing
- **Human-Readable Summaries** - No more cryptic diffs; get plain English explanations
- **Code-Aware Analysis** - Detects new functions, import changes, documentation updates
- **Multiple File Types** - Python, JavaScript, Markdown, JSON, YAML, and more
- **Watch Mode** - Automatically track changes as you work
- **Restore Capability** - Roll back to any previous version
- **Search History** - Find changes by keyword across all tracked files
- **Visual Dashboard** - HTML interface for browsing version history

## Installation

No dependencies required for basic usage (Python 3.7+).

```bash
# Clone or download to your project
cd doc-version-summaries

# Optional: Add to PATH for easy access
# Or run directly: python version_tracker.py
```

## Quick Start

### Track a File

```bash
# Start tracking a file
python version_tracker.py track myfile.py

# Track with custom display name
python version_tracker.py track config/settings.json --name "App Settings"
```

### View Changes

```bash
# See version history
python version_tracker.py history myfile.py

# Compare two versions
python version_tracker.py diff myfile.py --v1 2 --v2 3

# Summary of recent changes
python version_tracker.py summary myfile.py --since 7d
```

### Watch for Changes

```bash
# Watch a directory (auto-tracks supported file types)
python version_tracker.py watch ./src --interval 30

# Watch a single file
python version_tracker.py watch myfile.py
```

### Restore Previous Version

```bash
# Restore to specific version (creates new version first as backup)
python version_tracker.py restore myfile.py --version 3
```

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `track` | Start tracking a file | `track app.py` |
| `diff` | Show diff between versions | `diff app.py --v1 1 --v2 2` |
| `history` | Show version history | `history app.py --limit 10` |
| `summary` | Summarize changes since date | `summary app.py --since 7d` |
| `watch` | Watch path for changes | `watch ./src --interval 30` |
| `report` | Generate change report | `report --days 7` |
| `restore` | Restore to previous version | `restore app.py --version 3` |
| `search` | Search change summaries | `search "new function"` |
| `stats` | Show tracking statistics | `stats` |

All commands support `--json` flag for machine-readable output.

## Summary Intelligence

The tool analyzes changes contextually based on file type:

### Code Files (Python, JS, TS)
- Detects new/removed functions and classes
- Tracks import/dependency changes
- Notes documentation additions

### Markdown Files
- Identifies new sections (headings)
- Tracks list item additions
- Notes code block changes

### JSON Files
- Reports added/removed keys
- Tracks structural changes

### All Files
- Line additions/removals
- Similarity percentage
- Change magnitude (minor/moderate/significant/major)

## Example Output

```
🔄 UPDATED: app.py

Moderate changes to **app.py** (+45/-18 lines)

Changes:
  • Added new function(s) or class(es)
  • Added comments/documentation

Key additions:
  + def validate_user(user_id):
  + async def fetch_data(url):...

Version: 3
```

## Dashboard

Open `index.html` in a browser for a visual interface:

- Browse tracked files
- View version timeline
- Compare versions side-by-side
- See recent activity
- Search and filter

## Data Storage

All data is stored locally in the `data/` directory:

```
data/
├── index.json      # File metadata and version info
├── history.json    # Change log
└── versions/       # Stored file contents
    ├── abc123_v1.txt
    ├── abc123_v2.txt
    └── ...
```

## Integration Ideas

### Git Pre-Commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit
for file in $(git diff --cached --name-only); do
    python version_tracker.py track "$file"
done
```

### CI/CD Pipeline
```yaml
# Track documentation changes
- name: Track docs
  run: |
    python version_tracker.py track README.md
    python version_tracker.py track docs/*.md
```

### Cron Job for Reports
```bash
# Weekly report
0 9 * * 1 cd /path/to/project && python version_tracker.py report --days 7 >> reports/weekly.txt
```

## File Type Support

| Extension | Type | Intelligence |
|-----------|------|--------------|
| `.py` | Python | Functions, classes, imports |
| `.js` | JavaScript | Functions, requires |
| `.ts` | TypeScript | Functions, imports |
| `.md` | Markdown | Headings, lists, code blocks |
| `.json` | JSON | Key additions/removals |
| `.yaml/.yml` | YAML | Key tracking |
| `.txt` | Text | Line changes |
| `.html/.css` | Web | Line changes |
| `.sql` | SQL | Line changes |

## Tips

1. **Track early** - Start tracking files before major changes
2. **Use watch mode** - Let it auto-track during development sessions
3. **Check summaries** - Review before commits to ensure changes are intentional
4. **Search history** - Find when a feature was added or removed
5. **Restore safely** - Restoration creates a backup version first

## Limitations

- Text files only (no binary support)
- Local storage (not distributed)
- Single-user focused (no concurrent access handling)

## Contributing

This is part of the Guidebot feature pipeline. Improvements welcome!

## License

MIT
