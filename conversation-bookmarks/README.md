# Conversation Bookmarks

A dashboard for saving and reviewing important moments from voice conversations.

## Features

### 🔖 Bookmark Types
- **Insights** - Key learnings and analysis points
- **Action Items** - Tasks and follow-ups
- **Questions** - Important questions and answers
- **References** - Links, citations, and data points

### ⭐ Organization
- **Favorites** - Star important bookmarks for quick access
- **Tags** - Flexible tagging system with tag cloud
- **Search** - Full-text search across transcripts and notes
- **Filters** - Filter by type, favorites, or tags

### 📝 Rich Details
- Full transcript (user + assistant)
- Context information (when, where in conversation)
- Personal notes
- Audio playback (simulated waveform)
- Duration tracking

### 💾 Data Management
- Auto-saves to localStorage
- Export to JSON
- Import from JSON

## Voice Integration

Say these phrases during conversation to create bookmarks:
- "Bookmark this"
- "Save this moment"
- "Remember this"
- "Flag this"

The system captures:
1. The preceding context (last 30-60 seconds)
2. Timestamp
3. Auto-detected type based on content
4. Suggested tags from keywords

## Usage

### Viewing Bookmarks
1. Open `index.html` in browser
2. Browse all bookmarks in the list
3. Click any card to see full details
4. Use sidebar filters to narrow down

### Managing Bookmarks
- **Favorite**: Click star icon
- **Delete**: Click trash icon
- **Share**: Click share icon (copies to clipboard)
- **Edit Notes**: Type in the notes field (auto-saves)
- **Add Tags**: Type in tag field and press Enter

### Keyboard Shortcuts
- `/` - Focus search
- `Escape` - Clear selection

## Integration Points

### Voice Chat Integration
```javascript
// When user says "bookmark this"
function handleBookmarkRequest(context) {
    const bookmark = {
        id: Date.now(),
        title: generateTitle(context.transcript),
        timestamp: new Date().toISOString(),
        duration: context.duration,
        type: detectType(context.transcript),
        transcript: {
            user: context.userMessage,
            assistant: context.assistantResponse
        },
        context: [
            { icon: "clock", text: `${context.timeIntoConversation} into conversation` }
        ],
        tags: extractKeywords(context.transcript),
        notes: ""
    };
    
    saveBookmark(bookmark);
    announceBookmark(); // "Bookmarked!"
}
```

### Backend Sync
```python
# POST /api/bookmarks
{
    "action": "create",
    "bookmark": { ... }
}

# GET /api/bookmarks?filter=favorite&tag=market
{
    "bookmarks": [ ... ]
}
```

## File Structure

```
conversation-bookmarks/
├── index.html              # Main dashboard UI
├── README.md               # This file
└── bookmarks.json          # Exported bookmarks (user-generated)
```

## Built by PM2 for Guide Bot
