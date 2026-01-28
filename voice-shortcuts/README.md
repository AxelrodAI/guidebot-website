# Voice Shortcuts Dashboard

A UI for managing voice shortcut commands that map spoken phrases to multi-step workflows.

## Features

### 🎤 Trigger Phrases
- Define natural language phrases like "do the thing" or "check my portfolio"
- Shortcuts are learned over time based on user's verbal patterns
- Case-insensitive matching

### 📋 Multi-Step Workflows
- Each shortcut can map to multiple sequential actions
- Visual workflow builder with drag-and-drop step ordering
- Steps execute in sequence when triggered

### 📊 Categories
- **Workflows** - Multi-step processes (morning routine, analysis flow)
- **Quick Queries** - Single-answer requests (portfolio check, market summary)
- **Navigation** - Open specific pages or views
- **Automation** - Trigger automated processes
- **Custom** - User-defined categories

### 📈 Usage Analytics
- Track how often each shortcut is used
- See "Top Used" shortcuts in sidebar
- Usage badges: High (50+), Medium (20+), Low

### 💾 Data Management
- **Export** - Download shortcuts as JSON
- **Import** - Load shortcuts from JSON file
- Auto-saves to localStorage

## Usage

### Creating a Shortcut
1. Click "New Shortcut" button
2. Enter trigger phrase (what you'll say)
3. Add description (optional)
4. Select category
5. Define workflow steps
6. Click "Save Shortcut"

### Managing Shortcuts
- **Edit** - Click any shortcut card
- **Duplicate** - Use copy button on card
- **Delete** - Use trash button on card
- **Search** - Filter by trigger, description, or step content
- **Filter** - Click category in sidebar

## Integration with Voice Chat

The shortcuts are stored in localStorage and can be synced with the voice chat backend:

```python
# Example: Load shortcuts from localStorage JSON
import json

def load_shortcuts():
    with open('voice-shortcuts.json', 'r') as f:
        return json.load(f)

def match_shortcut(transcript, shortcuts):
    transcript_lower = transcript.lower()
    for shortcut in shortcuts:
        if shortcut['trigger'].lower() in transcript_lower:
            return shortcut
    return None

def execute_workflow(shortcut):
    for i, step in enumerate(shortcut['steps']):
        print(f"Step {i+1}: {step}")
        # Execute step logic here
```

## File Structure

```
voice-shortcuts/
├── index.html          # Main dashboard UI
├── README.md           # This file
└── voice-shortcuts.json # Export/import data (user-generated)
```

## Keyboard Shortcuts

- `Escape` - Close modal

## API/Backend Integration Points

For full voice integration, connect to:

1. **Speech Recognition** - Transcribe voice to text
2. **Shortcut Matcher** - Match transcript to trigger phrases
3. **Workflow Executor** - Run the matched workflow steps
4. **Usage Tracker** - Increment usage counts

Example webhook payload:
```json
{
  "event": "shortcut_triggered",
  "shortcut_id": 1,
  "trigger": "morning routine",
  "steps": ["Check pre-market futures", "Scan overnight news", ...],
  "timestamp": "2026-01-27T09:00:00Z"
}
```

## Built by PM2 for Guide Bot
