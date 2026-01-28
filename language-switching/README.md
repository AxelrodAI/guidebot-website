# Multi-Language Code Switching

Seamlessly switch languages mid-conversation — AI detects and responds in your language automatically.

## Features

### Real-Time Language Detection
- Automatic detection of 12+ languages
- Confidence scoring with alternative suggestions
- Sub-50ms detection latency

### Supported Languages
- 🇺🇸 English
- 🇪🇸 Spanish (Español)
- 🇫🇷 French (Français)
- 🇩🇪 German (Deutsch)
- 🇯🇵 Japanese (日本語)
- 🇨🇳 Chinese (中文)
- 🇰🇷 Korean (한국어)
- 🇧🇷 Portuguese (Português)
- 🇮🇹 Italian (Italiano)
- 🇷🇺 Russian (Русский)
- 🇸🇦 Arabic (العربية)
- 🇮🇳 Hindi (हिन्दी)

### Live Transcript
- Color-coded language tags
- Real-time updates as you speak
- Visual indication of language switches

### Switch History
- Track all language transitions
- Timestamp for each switch
- Analytics on language usage patterns

### Settings
- **Auto Language Detection**: Toggle automatic detection on/off
- **Response Language Match**: AI responds in your detected language
- **Mixed Language Support**: Enable code-mixing within single utterances

## How It Works

1. **Detection**: Speech is analyzed in real-time using language identification models
2. **Classification**: Language is identified with confidence scoring
3. **Adaptation**: AI automatically switches response language to match
4. **Tracking**: All switches are logged for analytics

## Use Cases

- **Bilingual conversations**: Switch between languages naturally
- **International teams**: Collaborate in multiple languages
- **Language learning**: Practice with automatic language detection
- **Customer support**: Serve customers in their preferred language

## Dashboard UI

The dashboard provides:
- Current detected language with flag and confidence meter
- Waveform animation showing active listening
- Grid of supported languages (clickable)
- Live transcript with language-tagged lines
- Language switch history timeline
- Session statistics (switches, languages used, accuracy, latency)
- Configurable settings

## Testing

1. Open `index.html` in browser
2. Watch the simulated conversation auto-play
3. Click different languages in the grid to simulate detection
4. Observe the transcript updating with language tags
5. Check statistics updating in real-time
6. Toggle settings switches

## Technical Notes

- Language detection uses confidence thresholds (typically >85%)
- Alternative detections shown when confidence is close
- Mixed language (code-switching) handled with per-phrase detection
- Latency target: <50ms for seamless experience

---

Built for GuideBot Voice Assistant
