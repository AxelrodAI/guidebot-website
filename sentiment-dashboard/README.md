# Communication Sentiment Dashboard

Real-time sentiment tracking across all communication channels.

## Features

### Overall Sentiment Score
- **Circular gauge** showing overall sentiment (0-100)
- **Emoji indicator** matching sentiment level
- **Trend arrow** comparing to previous period
- **Breakdown bars** for positive/neutral/negative percentages

### Channel Monitoring
Track sentiment across:
- 📧 **Email** - Email communications
- 💬 **Slack** - Slack messages and threads
- 👥 **Teams** - Microsoft Teams chats
- 🎮 **Discord** - Discord servers and DMs
- 💭 **Live Chat** - Customer support chat

Each channel shows:
- Message count
- Sentiment score
- Positive/Neutral/Negative breakdown
- Click to drill down

### Sentiment Trend Chart
- 7-day line chart
- Stacked area view
- Positive (green), Neutral (yellow), Negative (red)
- Powered by Chart.js

### Contact Sentiment
- Per-person sentiment scores
- Role and message count
- Visual sentiment badges
- Identify relationship health at a glance

### Sentiment Alerts
- ⚠️ Declining sentiment warnings
- ℹ️ Pattern detection notifications
- ✅ Recovery confirmations
- Timestamped feed

### Key Phrases (Word Cloud)
- Sized by frequency
- Color-coded by sentiment
- Shuffled for visual variety
- Hover for mention counts

### Recent Message Feed
- Live message stream
- Color-coded by sentiment
- Source channel indicator
- Sentiment score per message

## Time Ranges
- 24 hours
- 7 days (default)
- 30 days
- 90 days

## Usage

1. Open `index.html` in browser
2. View overall sentiment at top
3. Check channel cards for per-source analysis
4. Review contact list for relationship health
5. Monitor alerts for issues
6. Click channels to drill down

## Integration Points
Ready for backend integration:
- Real sentiment analysis API
- NLP-based scoring
- Email/Slack/Teams webhooks
- Contact CRM sync
- Alerting rules engine

## Live Updates
- Auto-refreshes sentiment score every 5 seconds
- Click "Refresh" for full data reload
- Real-time message feed

Built by PM2 for the Clawdbot pipeline.
