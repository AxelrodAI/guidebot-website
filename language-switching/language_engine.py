#!/usr/bin/env python3
"""
Multi-Language Code Switching Engine
=====================================
Detects language mid-conversation and seamlessly switches response language.
Supports 50+ languages via langdetect with confidence scoring.

Usage:
    python language_engine.py detect -t "Bonjour, comment allez-vous?"
    python language_engine.py history
    python language_engine.py stats
    python language_engine.py switch -t "Now I'm speaking English"
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from collections import Counter

# Language detection - use langdetect if available, fallback to simple heuristics
try:
    from langdetect import detect, detect_langs
    from langdetect.lang_detect_exception import LangDetectException
    HAS_LANGDETECT = True
except ImportError:
    HAS_LANGDETECT = False

# Data file for persistence
DATA_DIR = Path(__file__).parent / "data"
HISTORY_FILE = DATA_DIR / "language_history.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

# Language code to name mapping (ISO 639-1)
LANGUAGE_NAMES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "nl": "Dutch", "ru": "Russian",
    "ja": "Japanese", "ko": "Korean", "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)", "ar": "Arabic", "hi": "Hindi",
    "bn": "Bengali", "pa": "Punjabi", "te": "Telugu", "mr": "Marathi",
    "ta": "Tamil", "ur": "Urdu", "gu": "Gujarati", "kn": "Kannada",
    "ml": "Malayalam", "th": "Thai", "vi": "Vietnamese", "id": "Indonesian",
    "ms": "Malay", "tl": "Tagalog", "sw": "Swahili", "pl": "Polish",
    "uk": "Ukrainian", "ro": "Romanian", "hu": "Hungarian", "cs": "Czech",
    "el": "Greek", "sv": "Swedish", "da": "Danish", "fi": "Finnish",
    "no": "Norwegian", "he": "Hebrew", "tr": "Turkish", "fa": "Persian"
}

# Simple fallback detection patterns when langdetect not available
FALLBACK_PATTERNS = {
    "es": ["hola", "como", "gracias", "buenos", "días", "qué", "está", "sí", "señor"],
    "fr": ["bonjour", "merci", "comment", "êtes", "vous", "oui", "très", "bien", "salut"],
    "de": ["guten", "tag", "danke", "wie", "geht", "ihnen", "ja", "nein", "bitte", "morgen"],
    "it": ["ciao", "come", "stai", "grazie", "buongiorno", "buonasera", "sì", "prego"],
    "pt": ["olá", "obrigado", "como", "você", "está", "bom", "dia", "sim", "não"],
    "ja": ["こんにちは", "ありがとう", "はい", "いいえ", "おはよう", "さようなら"],
    "ko": ["안녕", "감사", "네", "아니요", "좋아", "사랑"],
    "zh": ["你好", "谢谢", "是", "不是", "好", "再见"],
    "ru": ["привет", "спасибо", "да", "нет", "хорошо", "как"],
    "ar": ["مرحبا", "شكرا", "نعم", "لا", "كيف"],
    "hi": ["नमस्ते", "धन्यवाद", "हाँ", "नहीं", "कैसे"],
}

class LanguageEngine:
    """Multi-language detection and code-switching engine."""
    
    def __init__(self):
        self._ensure_data_dir()
        self.history = self._load_history()
        self.settings = self._load_settings()
        self.current_language = self.settings.get("default_language", "en")
        self.switch_count = 0
        
    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
    def _load_history(self) -> list:
        """Load language detection history."""
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_history(self):
        """Save language detection history."""
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.history[-1000:], f, indent=2, ensure_ascii=False)  # Keep last 1000
            
    def _load_settings(self) -> dict:
        """Load settings."""
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "default_language": "en",
            "auto_switch": True,
            "min_confidence": 0.7,
            "switch_threshold": 2  # Messages before confirming switch
        }
    
    def _save_settings(self):
        """Save settings."""
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=2)
    
    def _fallback_detect(self, text: str) -> tuple:
        """Simple pattern-based language detection fallback."""
        text_lower = text.lower()
        scores = {}
        
        for lang, patterns in FALLBACK_PATTERNS.items():
            score = sum(1 for p in patterns if p in text_lower)
            if score > 0:
                scores[lang] = score
        
        if scores:
            best_lang = max(scores, key=scores.get)
            confidence = min(scores[best_lang] / 3.0, 1.0)  # Normalize
            return best_lang, confidence
        
        # Check for non-ASCII characters suggesting specific scripts
        if any('\u4e00' <= c <= '\u9fff' for c in text):
            return "zh", 0.8
        if any('\u3040' <= c <= '\u30ff' for c in text):
            return "ja", 0.8
        if any('\uac00' <= c <= '\ud7af' for c in text):
            return "ko", 0.8
        if any('\u0600' <= c <= '\u06ff' for c in text):
            return "ar", 0.8
        if any('\u0900' <= c <= '\u097f' for c in text):
            return "hi", 0.8
        if any('\u0400' <= c <= '\u04ff' for c in text):
            return "ru", 0.8
            
        return "en", 0.5  # Default to English with low confidence
    
    def detect_language(self, text: str) -> dict:
        """
        Detect language of input text.
        
        Returns:
            dict with keys: language_code, language_name, confidence, all_detected
        """
        if not text or not text.strip():
            return {
                "language_code": self.current_language,
                "language_name": LANGUAGE_NAMES.get(self.current_language, "Unknown"),
                "confidence": 0.0,
                "all_detected": [],
                "error": "Empty input"
            }
        
        if HAS_LANGDETECT:
            try:
                # Get all detected languages with probabilities
                detected = detect_langs(text)
                primary = detected[0]
                lang_code = str(primary.lang)
                confidence = primary.prob
                
                all_detected = [
                    {"code": str(d.lang), "name": LANGUAGE_NAMES.get(str(d.lang), str(d.lang)), "confidence": round(d.prob, 3)}
                    for d in detected[:5]
                ]
            except LangDetectException as e:
                lang_code, confidence = self._fallback_detect(text)
                all_detected = [{"code": lang_code, "name": LANGUAGE_NAMES.get(lang_code, lang_code), "confidence": confidence}]
        else:
            lang_code, confidence = self._fallback_detect(text)
            all_detected = [{"code": lang_code, "name": LANGUAGE_NAMES.get(lang_code, lang_code), "confidence": confidence}]
        
        result = {
            "language_code": lang_code,
            "language_name": LANGUAGE_NAMES.get(lang_code, lang_code),
            "confidence": round(confidence, 3),
            "all_detected": all_detected,
            "text_sample": text[:100] + "..." if len(text) > 100 else text,
            "timestamp": datetime.now().isoformat(),
            "using_langdetect": HAS_LANGDETECT
        }
        
        # Record in history
        self.history.append(result)
        self._save_history()
        
        return result
    
    def process_and_switch(self, text: str) -> dict:
        """
        Process text and handle language switching logic.
        
        Returns detection result plus switching recommendation.
        """
        detection = self.detect_language(text)
        detected_lang = detection["language_code"]
        confidence = detection["confidence"]
        min_confidence = self.settings.get("min_confidence", 0.7)
        
        should_switch = False
        switch_message = None
        
        if detected_lang != self.current_language and confidence >= min_confidence:
            # Check recent history for consistency
            recent = self.history[-self.settings.get("switch_threshold", 2):]
            same_lang_count = sum(1 for h in recent if h.get("language_code") == detected_lang)
            
            if same_lang_count >= self.settings.get("switch_threshold", 2) or confidence > 0.9:
                old_lang = self.current_language
                self.current_language = detected_lang
                self.switch_count += 1
                should_switch = True
                switch_message = f"Switched from {LANGUAGE_NAMES.get(old_lang, old_lang)} to {LANGUAGE_NAMES.get(detected_lang, detected_lang)}"
                
                # Update settings with new current language
                self.settings["current_language"] = detected_lang
                self._save_settings()
        
        detection["current_language"] = self.current_language
        detection["should_switch"] = should_switch
        detection["switch_message"] = switch_message
        detection["total_switches"] = self.switch_count
        
        return detection
    
    def get_history(self, limit: int = 20) -> list:
        """Get recent language detection history."""
        return self.history[-limit:]
    
    def get_stats(self) -> dict:
        """Get language detection statistics."""
        if not self.history:
            return {"total_detections": 0, "languages": {}, "switches": 0}
        
        lang_counts = Counter(h.get("language_code") for h in self.history)
        total = len(self.history)
        
        # Calculate switches (when consecutive detections differ)
        switches = 0
        for i in range(1, len(self.history)):
            if self.history[i].get("language_code") != self.history[i-1].get("language_code"):
                switches += 1
        
        return {
            "total_detections": total,
            "languages": {
                LANGUAGE_NAMES.get(code, code): {
                    "count": count,
                    "percentage": round(count / total * 100, 1)
                }
                for code, count in lang_counts.most_common()
            },
            "most_used": LANGUAGE_NAMES.get(lang_counts.most_common(1)[0][0], "Unknown") if lang_counts else None,
            "total_switches": switches,
            "switch_rate": round(switches / total * 100, 1) if total > 1 else 0,
            "current_language": LANGUAGE_NAMES.get(self.current_language, self.current_language),
            "using_langdetect": HAS_LANGDETECT
        }
    
    def clear_history(self):
        """Clear all history."""
        self.history = []
        self._save_history()
        return {"status": "cleared", "message": "Language history cleared"}
    
    def set_default_language(self, lang_code: str) -> dict:
        """Set default language."""
        self.settings["default_language"] = lang_code
        self.current_language = lang_code
        self._save_settings()
        return {
            "status": "updated",
            "default_language": lang_code,
            "language_name": LANGUAGE_NAMES.get(lang_code, lang_code)
        }


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Language Code Switching Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python language_engine.py detect -t "Bonjour, comment ça va?"
  python language_engine.py switch -t "Now I'm speaking in English"
  python language_engine.py history --limit 10
  python language_engine.py stats
  python language_engine.py set-default -l es
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Detect command
    detect_parser = subparsers.add_parser("detect", help="Detect language of text")
    detect_parser.add_argument("-t", "--text", required=True, help="Text to analyze")
    
    # Switch command (detect + handle switching)
    switch_parser = subparsers.add_parser("switch", help="Process text and handle language switching")
    switch_parser.add_argument("-t", "--text", required=True, help="Text to process")
    
    # History command
    history_parser = subparsers.add_parser("history", help="Show detection history")
    history_parser.add_argument("--limit", type=int, default=20, help="Number of entries")
    
    # Stats command
    subparsers.add_parser("stats", help="Show language statistics")
    
    # Clear command
    subparsers.add_parser("clear", help="Clear history")
    
    # Set default command
    default_parser = subparsers.add_parser("set-default", help="Set default language")
    default_parser.add_argument("-l", "--lang", required=True, help="Language code (e.g., en, es, fr)")
    
    # Languages command
    subparsers.add_parser("languages", help="List supported languages")
    
    args = parser.parse_args()
    engine = LanguageEngine()
    
    if args.command == "detect":
        result = engine.detect_language(args.text)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    elif args.command == "switch":
        result = engine.process_and_switch(args.text)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if result.get("switch_message"):
            print(f"\n🔄 {result['switch_message']}")
            
    elif args.command == "history":
        history = engine.get_history(args.limit)
        print(json.dumps(history, indent=2, ensure_ascii=False))
        
    elif args.command == "stats":
        stats = engine.get_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        
    elif args.command == "clear":
        result = engine.clear_history()
        print(json.dumps(result, indent=2))
        
    elif args.command == "set-default":
        result = engine.set_default_language(args.lang)
        print(json.dumps(result, indent=2))
        
    elif args.command == "languages":
        print("Supported languages:")
        for code, name in sorted(LANGUAGE_NAMES.items(), key=lambda x: x[1]):
            print(f"  {code}: {name}")
            
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
