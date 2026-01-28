# Proactive Email Drafts

Auto-draft email responses based on context and patterns. Learns your writing style over time.

## Features

- **Smart Context Analysis**: Detects urgency, questions, meeting requests, action items
- **Priority Scoring**: 1-5 scale based on email signals
- **Style Learning**: Learns from your sent responses (greetings, closings, length)
- **Placeholder Markers**: Highlights areas needing your input
- **Confidence Scoring**: Rates how confident the draft is
- **Batch Processing**: Generate drafts for multiple emails at once

## Installation

```bash
pip install python-dateutil  # Optional, for date parsing
```

No external dependencies required for core functionality.

## Quick Start

```bash
# Analyze an email
python email_drafter.py analyze -f email.json

# Generate a draft response
python email_drafter.py draft -f email.json

# Import emails for batch processing
python email_drafter.py import -f emails.json

# Generate drafts for all pending emails
python email_drafter.py batch --limit 10

# List all drafts
python email_drafter.py list drafts

# View statistics
python email_drafter.py stats
```

## Commands

### analyze
Analyze an email for context signals (urgency, questions, etc.)
```bash
python email_drafter.py analyze -f email.json --json
```

### draft
Generate a draft response for an email.
```bash
python email_drafter.py draft -f email.json
python email_drafter.py draft -e EMAIL_ID  # From stored emails
```

### list
List drafts or imported emails.
```bash
python email_drafter.py list drafts --status draft
python email_drafter.py list emails --limit 20
```

### import
Import emails for drafting.
```bash
python email_drafter.py import -f emails.json
```

### batch
Generate drafts for all pending emails.
```bash
python email_drafter.py batch --min-priority 4 --limit 10
```

### edit
Edit or update draft status.
```bash
python email_drafter.py edit DRAFT_ID --status sent
python email_drafter.py edit DRAFT_ID --body "New response text"
```

### discard
Remove drafts.
```bash
python email_drafter.py discard DRAFT_ID
python email_drafter.py discard --all
```

### learn
Learn from your actual sent responses to improve future drafts.
```bash
python email_drafter.py learn -f response.json
python email_drafter.py learn -f response.json -o ORIGINAL_EMAIL_ID
```

### style
View or update your writing style profile.
```bash
python email_drafter.py style
python email_drafter.py style --set-formality 0.8  # More formal (0-1)
```

### config
View or update configuration.
```bash
python email_drafter.py config
python email_drafter.py config --key user_name --value "John Doe"
python email_drafter.py config --key urgency_keywords --value '["urgent","asap","critical"]'
```

### stats
View drafting statistics.
```bash
python email_drafter.py stats
```

## Email JSON Format

```json
{
  "from": "sender@example.com",
  "subject": "Q4 Planning Meeting Request",
  "body": "Hi,\n\nCan we schedule a meeting this week to discuss Q4 planning?\n\nThanks,\nJohn",
  "received": "2025-01-27T10:30:00Z"
}
```

## Context Analysis

The system detects:
- **Urgency**: Keywords like "urgent", "ASAP", "deadline", etc.
- **Questions**: Sentences with ? or question keywords
- **Meeting Requests**: Keywords like "meeting", "schedule", "call"
- **Action Items**: Keywords like "action", "task", "review", "approve"
- **Sentiment**: Positive, negative, or neutral tone

## Priority Scoring

| Priority | Description |
|----------|-------------|
| 5 ⭐⭐⭐⭐⭐ | Urgent + multiple signals |
| 4 ⭐⭐⭐⭐ | High urgency or meeting request |
| 3 ⭐⭐⭐ | Standard email needing response |
| 2 ⭐⭐ | Low priority |
| 1 ⭐ | Informational only |

## Configuration Options

| Key | Description | Default |
|-----|-------------|---------|
| `user_name` | Your name for signatures | "User" |
| `response_tone` | professional/casual/formal | "professional" |
| `signature` | Closing signature | "Best regards" |
| `min_priority_for_draft` | Min priority to auto-draft | 3 |
| `urgency_keywords` | Words that indicate urgency | [...] |

## Integration Points

### Email Client Integration
Connect to email APIs (IMAP, Gmail API, Outlook) to:
1. Fetch new emails → `import`
2. Auto-generate drafts → `batch`
3. Send edited drafts → `edit --status sent`

### LLM Enhancement
The generated drafts use templates. Enhance with LLM:
1. Replace `[PLACEHOLDER]` markers with LLM completions
2. Use email body for context
3. Apply learned style profile

### Workflow Automation
```bash
# Example cron job
0 9 * * * cd /path/to/email-drafts && python email_drafter.py batch --min-priority 3
```

## Data Files

- `data/emails.json` - Imported emails
- `data/drafts.json` - Generated drafts
- `data/style_profile.json` - Learned writing style
- `data/config.json` - Configuration

---
Built by PM3 (Backend/Data Builder) | Proactive Email Drafts v1.0
