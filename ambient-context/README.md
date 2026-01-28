# Ambient Sound Context

Detect background sounds (coffee shop, office, car) to contextualize responses. Adjusts verbosity and tone based on environment.

## Concept

When you're driving, you need short responses. When you're at home in quiet, you can handle detailed explanations. This engine detects where you are and adjusts accordingly.

## Environments

| Environment | Emoji | Max Words | Tone | Use Case |
|-------------|-------|-----------|------|----------|
| Quiet | 🤫 | 500 | Conversational | Home, library, private office |
| Office | 🏢 | 200 | Professional | Open floor, meetings nearby |
| Coffee Shop | ☕ | 150 | Casual | Background chatter, music |
| Car | 🚗 | 50 | Direct | Driving - SAFETY FIRST |
| Outdoor | 🌳 | 100 | Clear | Wind, traffic, nature sounds |
| Crowd | 👥 | 30 | Brief | Event, party, street |

## CLI Usage

```bash
# Analyze an audio file
python ambient_engine.py analyze -f recording.wav

# Simulate an environment (for testing)
python ambient_engine.py simulate -e car
python ambient_engine.py simulate -e coffee_shop

# Get current context and guidelines
python ambient_engine.py context

# List all environments
python ambient_engine.py environments

# Manual override (force specific environment)
python ambient_engine.py override -e quiet
python ambient_engine.py override --clear

# View history
python ambient_engine.py history --limit 10

# Statistics
python ambient_engine.py stats

# Clear history
python ambient_engine.py clear
```

## Example Output

```bash
$ python ambient_engine.py simulate -e car
{
  "environment": "car",
  "environment_name": "In Car",
  "emoji": "🚗",
  "confidence": 0.95,
  "simulated": true,
  "response_guidelines": {
    "verbosity": "minimal",
    "max_words": 50,
    "tone": "direct",
    "features": {
      "detailed_explanations": false,
      "examples": false,
      "follow_up_questions": false,
      "tangents_ok": false
    }
  }
}

🚗 Simulated: In Car
📝 Max words: 50
🎯 Tone: direct
```

## API (Python)

```python
from ambient_engine import AmbientEngine

engine = AmbientEngine()

# Analyze audio
result = engine.analyze_audio("ambient.wav")
print(f"Detected: {result['environment_name']}")

# Or simulate for testing
result = engine.simulate_environment("coffee_shop")

# Get current guidelines
context = engine.get_current_context()
max_words = context["response_guidelines"]["max_words"]
tone = context["response_guidelines"]["tone"]

# Use in your assistant
if context["environment"] == "car":
    response = generate_short_response(query)
else:
    response = generate_full_response(query)
```

## Response Guidelines by Environment

### 🤫 Quiet (Home/Library)
- Full detailed explanations
- Include examples
- Ask follow-up questions
- Tangents are OK
- Up to 500 words

### 🏢 Office
- Professional tone
- Moderate detail
- Skip examples
- No tangents
- Up to 200 words

### ☕ Coffee Shop
- Casual and friendly
- Get to the point
- Still allow follow-ups
- Up to 150 words

### 🚗 In Car (SAFETY FIRST!)
- Essential info ONLY
- Ultra concise
- No follow-ups
- No explanations
- MAX 50 words

### 🌳 Outdoor
- Clear and direct
- Account for noise
- Keep it brief
- Up to 100 words

### 👥 Crowd
- One sentence if possible
- Save details for later
- MAX 30 words

## Integration with Voice Chat

1. Capture ambient audio (first few seconds of listening)
2. Call `engine.analyze_audio()` or use pre-trained model
3. Get `response_guidelines` from context
4. Pass guidelines to response generation
5. Periodically re-check environment (every few minutes)

## Files

- `ambient_engine.py` - Python engine with CLI
- `README.md` - This documentation
- `data/` - Persistent storage for history and settings

## Future Enhancements

- Integration with YAMNet/VGGish for real ML-based audio classification
- Real-time continuous monitoring
- User preference learning
- Time-of-day awareness
- Location integration (GPS + audio)
