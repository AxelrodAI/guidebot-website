#!/usr/bin/env python3
"""
Ambient Sound Context Engine
=============================
Detects background sounds to contextualize responses.
Adjusts response verbosity based on environment.

Environments:
- quiet: Detailed responses OK
- office: Professional, moderate length
- coffee_shop: Moderate, casual tone
- car: Short, essential info only
- outdoor: Clear, concise
- crowd: Very brief responses

Usage:
    python ambient_engine.py analyze -f audio.wav
    python ambient_engine.py simulate -e car
    python ambient_engine.py context
    python ambient_engine.py config
    python ambient_engine.py stats
"""

import argparse
import json
import os
import sys
import random
import wave
import struct
from datetime import datetime
from pathlib import Path
from collections import Counter

# Data directory for persistence
DATA_DIR = Path(__file__).parent / "data"
HISTORY_FILE = DATA_DIR / "context_history.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

# Environment definitions with response guidelines
ENVIRONMENTS = {
    "quiet": {
        "name": "Quiet",
        "emoji": "🤫",
        "description": "Low background noise - home, library, private office",
        "verbosity": "full",
        "max_words": 500,
        "tone": "conversational",
        "features": {
            "detailed_explanations": True,
            "examples": True,
            "follow_up_questions": True,
            "tangents_ok": True
        },
        "noise_range": (0, 30)  # dB
    },
    "office": {
        "name": "Office",
        "emoji": "🏢",
        "description": "Moderate office noise - open floor, meetings nearby",
        "verbosity": "moderate",
        "max_words": 200,
        "tone": "professional",
        "features": {
            "detailed_explanations": True,
            "examples": False,
            "follow_up_questions": True,
            "tangents_ok": False
        },
        "noise_range": (30, 50)
    },
    "coffee_shop": {
        "name": "Coffee Shop",
        "emoji": "☕",
        "description": "Background chatter, music, espresso machines",
        "verbosity": "moderate",
        "max_words": 150,
        "tone": "casual",
        "features": {
            "detailed_explanations": False,
            "examples": False,
            "follow_up_questions": True,
            "tangents_ok": False
        },
        "noise_range": (50, 65)
    },
    "car": {
        "name": "In Car",
        "emoji": "🚗",
        "description": "Driving - road noise, engine, focus on safety",
        "verbosity": "minimal",
        "max_words": 50,
        "tone": "direct",
        "features": {
            "detailed_explanations": False,
            "examples": False,
            "follow_up_questions": False,
            "tangents_ok": False
        },
        "noise_range": (55, 75)
    },
    "outdoor": {
        "name": "Outdoor",
        "emoji": "🌳",
        "description": "Outside - wind, traffic, nature sounds",
        "verbosity": "concise",
        "max_words": 100,
        "tone": "clear",
        "features": {
            "detailed_explanations": False,
            "examples": False,
            "follow_up_questions": True,
            "tangents_ok": False
        },
        "noise_range": (40, 70)
    },
    "crowd": {
        "name": "Crowd",
        "emoji": "👥",
        "description": "Crowded space - event, party, street",
        "verbosity": "minimal",
        "max_words": 30,
        "tone": "brief",
        "features": {
            "detailed_explanations": False,
            "examples": False,
            "follow_up_questions": False,
            "tangents_ok": False
        },
        "noise_range": (70, 90)
    },
    "unknown": {
        "name": "Unknown",
        "emoji": "❓",
        "description": "Unable to determine environment",
        "verbosity": "moderate",
        "max_words": 200,
        "tone": "neutral",
        "features": {
            "detailed_explanations": True,
            "examples": False,
            "follow_up_questions": True,
            "tangents_ok": False
        },
        "noise_range": (0, 100)
    }
}

# Audio feature patterns for environment classification (simplified)
# In production, use actual audio ML models like YAMNet, VGGish, or similar
AUDIO_PATTERNS = {
    "quiet": {
        "continuous_low_freq": True,
        "speech_detected": False,
        "transient_sounds": False,
        "music_detected": False
    },
    "office": {
        "keyboard_sounds": True,
        "distant_speech": True,
        "hvac_hum": True,
        "phone_rings": True
    },
    "coffee_shop": {
        "espresso_sounds": True,
        "casual_chatter": True,
        "background_music": True,
        "dishes_clinking": True
    },
    "car": {
        "engine_hum": True,
        "road_noise": True,
        "wind_buffeting": True,
        "turn_signals": True
    },
    "outdoor": {
        "wind_noise": True,
        "birds_insects": True,
        "distant_traffic": True,
        "footsteps": True
    },
    "crowd": {
        "many_voices": True,
        "music_loud": True,
        "cheering": True,
        "general_noise": True
    }
}


class AmbientEngine:
    """Ambient sound context detection and response adjustment engine."""
    
    def __init__(self):
        self._ensure_data_dir()
        self.history = self._load_history()
        self.settings = self._load_settings()
        self.current_environment = self.settings.get("default_environment", "unknown")
        self.confidence = 0.0
        
    def _ensure_data_dir(self):
        """Create data directory if needed."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
    def _load_history(self) -> list:
        """Load context detection history."""
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_history(self):
        """Save context history."""
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.history[-500:], f, indent=2)  # Keep last 500
            
    def _load_settings(self) -> dict:
        """Load settings."""
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "default_environment": "unknown",
            "auto_adjust": True,
            "sensitivity": 0.7,
            "override_enabled": True,
            "manual_override": None
        }
    
    def _save_settings(self):
        """Save settings."""
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=2)
    
    def _analyze_audio_features(self, audio_path: str) -> dict:
        """
        Analyze audio file for environment classification.
        
        In production, this would use ML models. Here we use basic signal analysis.
        """
        try:
            with wave.open(audio_path, 'rb') as wf:
                n_channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                
                # Read all frames
                frames = wf.readframes(n_frames)
                
                # Convert to samples
                if sample_width == 2:
                    fmt = f"<{n_frames * n_channels}h"
                    samples = struct.unpack(fmt, frames)
                else:
                    samples = list(frames)
                
                # Basic audio features
                samples_abs = [abs(s) for s in samples]
                avg_amplitude = sum(samples_abs) / len(samples_abs) if samples_abs else 0
                max_amplitude = max(samples_abs) if samples_abs else 0
                
                # Estimate dB (simplified)
                if avg_amplitude > 0:
                    db_estimate = 20 * (avg_amplitude / 32768) * 100  # Rough scaling
                else:
                    db_estimate = 0
                
                # Variance for detecting transients
                mean_sq = sum(s**2 for s in samples) / len(samples) if samples else 0
                variance = mean_sq - (sum(samples) / len(samples))**2 if samples else 0
                
                return {
                    "duration_sec": n_frames / framerate,
                    "sample_rate": framerate,
                    "channels": n_channels,
                    "avg_amplitude": avg_amplitude,
                    "max_amplitude": max_amplitude,
                    "estimated_db": round(db_estimate, 1),
                    "variance": variance,
                    "has_transients": variance > (avg_amplitude * 2)
                }
                
        except Exception as e:
            return {"error": str(e)}
    
    def _classify_environment(self, features: dict) -> tuple:
        """
        Classify environment based on audio features.
        Returns (environment, confidence).
        """
        if "error" in features:
            return "unknown", 0.0
        
        db = features.get("estimated_db", 50)
        has_transients = features.get("has_transients", False)
        
        # Match against noise ranges
        candidates = []
        for env, config in ENVIRONMENTS.items():
            if env == "unknown":
                continue
            low, high = config["noise_range"]
            if low <= db <= high:
                # Calculate how well it fits the range
                range_size = high - low
                center = (low + high) / 2
                distance = abs(db - center)
                fit = 1 - (distance / (range_size / 2))
                candidates.append((env, fit))
        
        if candidates:
            # Sort by fit score
            candidates.sort(key=lambda x: x[1], reverse=True)
            best_env, confidence = candidates[0]
            
            # Boost or reduce based on transients
            if best_env in ["car", "crowd", "coffee_shop"] and has_transients:
                confidence = min(confidence + 0.1, 1.0)
            elif best_env == "quiet" and has_transients:
                confidence = max(confidence - 0.2, 0.3)
            
            return best_env, round(confidence, 2)
        
        return "unknown", 0.5
    
    def analyze_audio(self, audio_path: str) -> dict:
        """
        Analyze audio file and detect environment.
        """
        features = self._analyze_audio_features(audio_path)
        env, confidence = self._classify_environment(features)
        
        self.current_environment = env
        self.confidence = confidence
        
        env_config = ENVIRONMENTS[env]
        
        result = {
            "environment": env,
            "environment_name": env_config["name"],
            "emoji": env_config["emoji"],
            "confidence": confidence,
            "audio_features": features,
            "response_guidelines": {
                "verbosity": env_config["verbosity"],
                "max_words": env_config["max_words"],
                "tone": env_config["tone"],
                "features": env_config["features"]
            },
            "timestamp": datetime.now().isoformat()
        }
        
        self.history.append(result)
        self._save_history()
        
        return result
    
    def simulate_environment(self, environment: str) -> dict:
        """
        Simulate detection of a specific environment (for testing).
        """
        if environment not in ENVIRONMENTS:
            return {"error": f"Unknown environment: {environment}. Valid: {list(ENVIRONMENTS.keys())}"}
        
        self.current_environment = environment
        self.confidence = 0.95  # High confidence for simulation
        
        env_config = ENVIRONMENTS[environment]
        
        result = {
            "environment": environment,
            "environment_name": env_config["name"],
            "emoji": env_config["emoji"],
            "confidence": self.confidence,
            "simulated": True,
            "response_guidelines": {
                "verbosity": env_config["verbosity"],
                "max_words": env_config["max_words"],
                "tone": env_config["tone"],
                "features": env_config["features"]
            },
            "timestamp": datetime.now().isoformat()
        }
        
        self.history.append(result)
        self._save_history()
        
        return result
    
    def get_current_context(self) -> dict:
        """
        Get current environment context and response guidelines.
        """
        env = self.current_environment
        env_config = ENVIRONMENTS.get(env, ENVIRONMENTS["unknown"])
        
        return {
            "environment": env,
            "environment_name": env_config["name"],
            "emoji": env_config["emoji"],
            "confidence": self.confidence,
            "description": env_config["description"],
            "response_guidelines": {
                "verbosity": env_config["verbosity"],
                "max_words": env_config["max_words"],
                "tone": env_config["tone"],
                "features": env_config["features"]
            },
            "recommendation": self._get_recommendation(env)
        }
    
    def _get_recommendation(self, env: str) -> str:
        """Generate human-readable recommendation."""
        recommendations = {
            "quiet": "Full detail responses OK. Can include examples and ask follow-up questions.",
            "office": "Keep responses professional and moderate length. Skip tangents.",
            "coffee_shop": "Casual tone, moderate length. Get to the point but stay friendly.",
            "car": "SAFETY FIRST. Very short responses only. Essential info only. No long explanations.",
            "outdoor": "Clear and concise. Speak up and be direct.",
            "crowd": "Ultra brief. One sentence if possible. Save details for later.",
            "unknown": "Default to moderate detail. Adjust if user requests."
        }
        return recommendations.get(env, recommendations["unknown"])
    
    def set_manual_override(self, environment: str = None) -> dict:
        """
        Set manual environment override.
        Pass None to clear override.
        """
        if environment and environment not in ENVIRONMENTS:
            return {"error": f"Unknown environment: {environment}"}
        
        self.settings["manual_override"] = environment
        self._save_settings()
        
        if environment:
            self.current_environment = environment
            self.confidence = 1.0
            return {
                "status": "override_set",
                "environment": environment,
                "message": f"Manual override set to {ENVIRONMENTS[environment]['name']}"
            }
        else:
            return {
                "status": "override_cleared",
                "message": "Manual override cleared. Auto-detection active."
            }
    
    def get_history(self, limit: int = 20) -> list:
        """Get recent context history."""
        return self.history[-limit:]
    
    def get_stats(self) -> dict:
        """Get environment detection statistics."""
        if not self.history:
            return {"total_detections": 0, "environments": {}}
        
        env_counts = Counter(h.get("environment") for h in self.history)
        total = len(self.history)
        
        return {
            "total_detections": total,
            "environments": {
                ENVIRONMENTS.get(env, {}).get("name", env): {
                    "count": count,
                    "percentage": round(count / total * 100, 1),
                    "emoji": ENVIRONMENTS.get(env, {}).get("emoji", "?")
                }
                for env, count in env_counts.most_common()
            },
            "most_common": ENVIRONMENTS.get(env_counts.most_common(1)[0][0], {}).get("name") if env_counts else None,
            "current_environment": ENVIRONMENTS.get(self.current_environment, {}).get("name", "Unknown"),
            "current_confidence": self.confidence,
            "auto_adjust_enabled": self.settings.get("auto_adjust", True),
            "manual_override": self.settings.get("manual_override")
        }
    
    def list_environments(self) -> dict:
        """List all supported environments."""
        return {
            env: {
                "name": config["name"],
                "emoji": config["emoji"],
                "description": config["description"],
                "verbosity": config["verbosity"],
                "max_words": config["max_words"],
                "tone": config["tone"]
            }
            for env, config in ENVIRONMENTS.items()
            if env != "unknown"
        }
    
    def clear_history(self) -> dict:
        """Clear detection history."""
        self.history = []
        self._save_history()
        return {"status": "cleared", "message": "Context history cleared"}


def main():
    parser = argparse.ArgumentParser(
        description="Ambient Sound Context Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ambient_engine.py analyze -f audio.wav
  python ambient_engine.py simulate -e car
  python ambient_engine.py context
  python ambient_engine.py environments
  python ambient_engine.py override -e quiet
  python ambient_engine.py override --clear
  python ambient_engine.py stats
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Analyze audio
    analyze_parser = subparsers.add_parser("analyze", help="Analyze audio file")
    analyze_parser.add_argument("-f", "--file", required=True, help="Audio file path (.wav)")
    
    # Simulate environment
    sim_parser = subparsers.add_parser("simulate", help="Simulate environment detection")
    sim_parser.add_argument("-e", "--environment", required=True, 
                           help="Environment: quiet, office, coffee_shop, car, outdoor, crowd")
    
    # Get current context
    subparsers.add_parser("context", help="Get current environment context")
    
    # List environments
    subparsers.add_parser("environments", help="List all supported environments")
    
    # Manual override
    override_parser = subparsers.add_parser("override", help="Set manual environment override")
    override_parser.add_argument("-e", "--environment", help="Environment to force")
    override_parser.add_argument("--clear", action="store_true", help="Clear override")
    
    # History
    history_parser = subparsers.add_parser("history", help="Show detection history")
    history_parser.add_argument("--limit", type=int, default=20, help="Number of entries")
    
    # Stats
    subparsers.add_parser("stats", help="Show statistics")
    
    # Clear
    subparsers.add_parser("clear", help="Clear history")
    
    args = parser.parse_args()
    engine = AmbientEngine()
    
    if args.command == "analyze":
        result = engine.analyze_audio(args.file)
        print(json.dumps(result, indent=2))
        print(f"\n{result['emoji']} Detected: {result['environment_name']} (confidence: {result['confidence']})")
        
    elif args.command == "simulate":
        result = engine.simulate_environment(args.environment)
        print(json.dumps(result, indent=2))
        if "error" not in result:
            print(f"\n{result['emoji']} Simulated: {result['environment_name']}")
            print(f"📝 Max words: {result['response_guidelines']['max_words']}")
            print(f"🎯 Tone: {result['response_guidelines']['tone']}")
        
    elif args.command == "context":
        result = engine.get_current_context()
        print(json.dumps(result, indent=2))
        print(f"\n{result['emoji']} Current: {result['environment_name']}")
        print(f"💡 {result['recommendation']}")
        
    elif args.command == "environments":
        result = engine.list_environments()
        print(json.dumps(result, indent=2))
        
    elif args.command == "override":
        if args.clear:
            result = engine.set_manual_override(None)
        elif args.environment:
            result = engine.set_manual_override(args.environment)
        else:
            result = {"error": "Specify --environment or --clear"}
        print(json.dumps(result, indent=2))
        
    elif args.command == "history":
        history = engine.get_history(args.limit)
        print(json.dumps(history, indent=2))
        
    elif args.command == "stats":
        stats = engine.get_stats()
        print(json.dumps(stats, indent=2))
        
    elif args.command == "clear":
        result = engine.clear_history()
        print(json.dumps(result, indent=2))
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
