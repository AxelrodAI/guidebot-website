# Ambient Sound Context

AI adapts responses based on your environment — shorter when driving, detailed when quiet.

## Features

### Real-Time Environment Detection
- Automatic detection of 8+ environments
- Confidence scoring for classification
- Sub-200ms detection latency

### Supported Environments
- ☕ Coffee Shop (moderate noise)
- 🏠 Home (quiet)
- 🚗 Car - Driving (road noise)
- 🏢 Office (background chatter)
- 🚇 Public Transit (crowd noise)
- 🏞️ Outdoor - Park (nature sounds)
- 🏋️ Gym (music & equipment)
- 📚 Library (very quiet)

### Sound Categories Detected
- 💬 Speech/Voices
- ☕ Coffee Machine sounds
- 🎵 Background Music
- 🚶 Footsteps
- 🍽️ Dishes/Cutlery
- 📱 Typing/Tapping
- 🚗 Traffic
- 🌬️ HVAC/Fans
- 🔔 Notifications

### Response Modes
| Mode | Description | Use Case |
|------|-------------|----------|
| ⚡ Brief | Short, essential info only | High noise, transit |
| ⚖️ Balanced | Concise but complete | Office, coffee shop |
| 📝 Detailed | Full explanations | Quiet home, library |
| 🎤 Hands-Free | Voice-optimized, driving mode | Car, exercising |

### AI Adaptation
- **Response Length**: Auto-adjusts word count (20-200 words)
- **Speech Rate**: Voice speed matches environment pace
- **Focus Priority**: Emphasizes key points vs full context

## How It Works

1. **Listen**: Continuously analyze ambient audio
2. **Classify**: Identify environment from sound signatures
3. **Adapt**: Automatically adjust response parameters
4. **Track**: Log environment changes for analytics

## Use Cases

- **Driving**: "You're in the car — I'll keep it brief and hands-free"
- **Office**: "Moderate noise detected — balanced responses"
- **Home at night**: "Quiet environment — I can be more detailed"
- **Gym**: "High noise — essential info only, louder speech"

## Dashboard UI

The dashboard provides:
- Current environment with icon and confidence
- Live sound spectrum visualization
- Response mode cards (auto-selected based on environment)
- Sound category detection with levels
- Environment history timeline
- AI adaptation settings display
- Session statistics

## Testing

1. Open `index.html` in browser
2. Watch environment auto-cycle through different types
3. Observe response mode auto-selecting based on environment
4. Check sound categories fluctuating
5. Monitor adaptation settings changing
6. Click mode cards to manually override

## Technical Notes

- Uses audio classification model for environment detection
- Sound categories analyzed via frequency spectrum
- Noise level measured in decibels (dB)
- Smooth transitions between modes (no jarring changes)
- User can always override auto-selected mode

## Privacy

- Audio processed locally, not uploaded
- Only classification results stored, not raw audio
- Environment history can be cleared
- Detection can be paused anytime

---

Built for GuideBot Voice Assistant
