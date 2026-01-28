# Voice Mood Detection Dashboard

Real-time visualization of detected moods during voice conversations, with adaptive response settings.

## Features

### 🎭 Mood Detection
Detects 6 primary moods from voice analysis:
- **Calm** 😌 - Relaxed speech, steady pace
- **Happy** 😊 - Energized, animated pitch
- **Neutral** 😐 - Baseline, balanced
- **Stressed** 😰 - Fast speech, tense
- **Tired** 😴 - Slow, low energy
- **Frustrated** 😤 - Clipped speech, sighing

### 📊 Voice Indicators
Real-time analysis of:
- **Speech Rate** - Words per minute (slow/normal/fast)
- **Volume** - Low to high amplitude
- **Pitch Variation** - Flat vs animated
- **Pause Frequency** - Fluent vs hesitant

### 📈 Mood Timeline
Interactive chart showing mood changes over time:
- 5 minute, 15 minute, 30 minute, 1 hour views
- Hover for detailed timestamps
- Smooth trend visualization

### ⚙️ Adaptive Response Settings
Configure how ClawD responds to each mood:
| Mood | Response Style |
|------|---------------|
| Calm | Detailed explanations |
| Happy | Enthusiastic, match energy |
| Neutral | Balanced, standard |
| Stressed | Calm, clear, supportive |
| Tired | Concise, suggest breaks |
| Frustrated | Patient, acknowledge feelings |

### 💡 AI Suggestions
Real-time recommendations based on current mood:
- Best tasks for current energy level
- When to suggest breaks
- Interaction style tips

### 📜 Session History
Track mood transitions throughout the conversation:
- Timestamp of each mood change
- Duration in each state
- Visual emoji indicators

## Technical Implementation

### Voice Analysis Features
```python
# Features extracted for mood detection
features = {
    'pitch_mean': float,      # Average pitch in Hz
    'pitch_std': float,       # Pitch variation
    'speech_rate': float,     # Words per minute
    'volume_mean': float,     # Average amplitude
    'pause_ratio': float,     # Silence vs speech ratio
    'energy': float,          # Overall energy level
}
```

### Mood Classification Model
- Input: 6 voice features
- Output: Mood probability distribution
- Confidence threshold: 70%

### API Integration
```javascript
// Webhook for mood updates
{
    "event": "mood_detected",
    "mood": "happy",
    "confidence": 0.87,
    "indicators": {
        "speech_rate": 145,
        "volume": "medium-high",
        "pitch": "high",
        "pauses": "low"
    },
    "timestamp": "2026-01-27T21:15:00Z"
}

// Response style adjustment
{
    "mood": "stressed",
    "adjustments": {
        "response_length": "shorter",
        "tone": "calming",
        "complexity": "simplified"
    }
}
```

## Usage

1. Open `index.html` in browser
2. Dashboard shows simulated mood detection
3. Toggle "Adaptive Responses" to enable/disable
4. Click "Pause" to stop detection
5. Click "Reset" to clear session history

## File Structure

```
mood-detection/
├── index.html      # Dashboard UI with Chart.js
├── README.md       # This file
└── mood_detector.py # Backend detection (future)
```

## Integration Points

### Voice Chat Integration
```javascript
// On voice input
voiceChat.on('audio_chunk', (chunk) => {
    const features = extractFeatures(chunk);
    const mood = moodDetector.classify(features);
    
    if (mood.confidence > 0.7) {
        updateDashboard(mood);
        adjustResponseStyle(mood.label);
    }
});
```

### Break Suggestions
```javascript
// When tired mood persists
if (currentMood === 'tired' && moodDuration > 5 * 60) {
    suggestBreak("You sound tired. Want to take a short break?");
}
```

## Built by PM2 for Guide Bot
