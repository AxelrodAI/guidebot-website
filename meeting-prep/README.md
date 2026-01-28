# Smart Meeting Prep 📋

> Automatically gather attendee info, notes, and emails before meetings. Never walk into a meeting unprepared again.

## Overview

Smart Meeting Prep is an intelligent meeting preparation system that:

- 📅 **Syncs with your calendar** to find upcoming meetings
- 👥 **Researches attendees** - roles, recent interactions, communication styles
- 📧 **Surfaces relevant emails** - finds threads related to meeting topics
- 📄 **Gathers documents** - links to relevant files and previous notes
- 🤖 **Generates AI briefings** - talking points, questions to expect, and more
- 🎯 **Tracks prep score** - know when you're ready

## Quick Start

### Dashboard UI

Open `index.html` in your browser for the visual dashboard:

```bash
# Windows
start index.html

# Mac
open index.html

# Linux
xdg-open index.html
```

### Python CLI

```bash
# List upcoming meetings
python meeting_prep.py upcoming

# Full prep for a meeting
python meeting_prep.py prep -m mtg_001

# Get attendee intelligence
python meeting_prep.py attendees -m mtg_001

# Generate AI briefing
python meeting_prep.py briefing -m mtg_001

# Export prep kit to JSON
python meeting_prep.py export -m mtg_001 -o my-prep.json

# Search related content
python meeting_prep.py search -q "q4 planning"
```

## Features

### 1. Meeting Overview
See all upcoming meetings at a glance with:
- Time and duration
- Attendee list
- Meeting type (1:1, review, planning, external)
- Quick prep status

### 2. Attendee Intelligence
For each attendee, automatically gather:
- **Name & Role** - Who they are
- **Department** - Where they fit in the org
- **Last Interaction** - When you last communicated
- **Communication Style** - How they prefer to communicate
- **Recent Context** - Notes from previous meetings
- **LinkedIn Profile** - Quick access to their background

### 3. Related Documents
Automatically find and link:
- Previous meeting notes
- Shared documents
- Relevant spreadsheets
- Dashboards and trackers
- Email attachments

### 4. Email Thread Analysis
Surface relevant email threads:
- Filter by attendee
- Filter by topic/keywords
- Show most recent first
- Preview key content

### 5. AI Briefing Generation
One-click AI briefing includes:
- Executive summary
- Suggested talking points
- Potential questions to expect
- Recommended responses
- Pre-meeting checklist

### 6. Preparation Score
Track your readiness:
- Attendees researched (%)
- Documents gathered (%)
- Emails reviewed (%)
- Actions completed (%)
- Overall score with status

## Integration Points

### Calendar Integration
Connect to your calendar provider:
- Google Calendar
- Microsoft Outlook
- Apple Calendar
- CalDAV compatible

### Email Integration
Search and surface relevant emails:
- Gmail API
- Microsoft Graph (Outlook)
- IMAP compatible

### Document Storage
Find related files:
- Google Drive
- OneDrive/SharePoint
- Dropbox
- Local file system

### CRM Integration
Enrich attendee data:
- Salesforce
- HubSpot
- LinkedIn Sales Navigator

## Configuration

Create a `config.json` file to customize:

```json
{
  "calendar": {
    "provider": "google",
    "lookahead_days": 7
  },
  "email": {
    "provider": "gmail",
    "search_days": 30,
    "max_results": 10
  },
  "documents": {
    "provider": "google_drive",
    "auto_link": true
  },
  "briefing": {
    "style": "detailed",
    "include_questions": true,
    "include_checklist": true
  },
  "notifications": {
    "prep_reminder_hours": 2,
    "low_score_alert": 50
  }
}
```

## Workflow Examples

### Daily Prep Routine

1. Open dashboard or run `python meeting_prep.py upcoming`
2. For each meeting today, review prep score
3. Click into low-score meetings for detail
4. Generate briefings for important meetings
5. Complete pre-meeting actions

### Voice Integration

Say to Clawdbot:
- "What meetings do I have today?"
- "Prep me for my 2pm meeting"
- "Who's in my Q4 planning meeting?"
- "What should I know before talking to Sarah?"
- "Generate a briefing for my investor call"

### Automation

Set up automatic prep:
- 2 hours before: Send prep reminder if score < 80%
- 1 hour before: Auto-generate briefing
- 15 min before: Push notification with key points
- After meeting: Prompt for notes

## API Reference

### `get_upcoming_meetings(days: int) -> List[Meeting]`
Returns meetings in the next N days.

### `get_attendee_intel(email: str) -> AttendeeIntel`
Returns intelligence on a specific attendee.

### `get_related_emails(meeting_id: str) -> List[Email]`
Finds emails related to a meeting.

### `get_related_documents(meeting_id: str) -> List[Document]`
Finds documents related to a meeting.

### `generate_briefing(meeting: Meeting) -> str`
Generates an AI briefing for the meeting.

### `calculate_prep_score(meeting: Meeting) -> PrepScore`
Calculates preparation readiness score.

## Testing

```bash
# Run all tests
python -m pytest tests/

# Test with sample data
python meeting_prep.py upcoming
python meeting_prep.py prep -m mtg_001
python meeting_prep.py briefing -m mtg_001
```

## Roadmap

- [x] Basic dashboard UI
- [x] Python CLI backend
- [x] Sample data generation
- [ ] Google Calendar integration
- [ ] Gmail integration
- [ ] Google Drive integration
- [ ] Real AI briefing generation
- [ ] Meeting notes capture post-meeting
- [ ] Action item extraction
- [ ] Mobile notifications

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Smart Meeting Prep                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │
│  │   Calendar   │   │    Email     │   │   Documents  │    │
│  │  Integration │   │  Integration │   │  Integration │    │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘    │
│         │                  │                  │             │
│         ▼                  ▼                  ▼             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Prep Engine (meeting_prep.py)            │  │
│  │  - Meeting aggregation                               │  │
│  │  - Attendee intelligence                             │  │
│  │  - Content relevance scoring                         │  │
│  │  - Briefing generation                               │  │
│  └──────────────────────────────────────────────────────┘  │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Presentation Layer                          │  │
│  │  ┌────────────────┐    ┌────────────────┐            │  │
│  │  │  Dashboard UI  │    │   CLI Output   │            │  │
│  │  │  (index.html)  │    │  (terminal)    │            │  │
│  │  └────────────────┘    └────────────────┘            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## License

MIT License - Part of Clawdbot project.
