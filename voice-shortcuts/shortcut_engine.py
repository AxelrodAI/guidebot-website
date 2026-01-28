#!/usr/bin/env python3
"""
Voice Shortcut Engine
Matches spoken phrases to configured shortcuts and executes workflows.
"""

import json
import os
from datetime import datetime
from pathlib import Path
import re
from typing import Optional, Dict, List, Any

# Default shortcuts file
SHORTCUTS_FILE = Path(__file__).parent / "voice_shortcuts.json"
USAGE_LOG_FILE = Path(__file__).parent / "shortcut_usage.json"


class ShortcutEngine:
    """Engine for matching and executing voice shortcuts."""
    
    def __init__(self, shortcuts_file: str = None):
        self.shortcuts_file = Path(shortcuts_file) if shortcuts_file else SHORTCUTS_FILE
        self.shortcuts: List[Dict] = []
        self.usage_log: Dict = {}
        self.load_shortcuts()
        self.load_usage_log()
    
    def load_shortcuts(self):
        """Load shortcuts from JSON file."""
        if self.shortcuts_file.exists():
            with open(self.shortcuts_file, 'r') as f:
                self.shortcuts = json.load(f)
        else:
            # Default shortcuts
            self.shortcuts = [
                {
                    "id": 1,
                    "trigger": "check my portfolio",
                    "description": "Get a quick summary of current positions and P&L",
                    "category": "query",
                    "steps": [
                        "Open portfolio dashboard",
                        "Calculate current P&L",
                        "Summarize top movers"
                    ],
                    "usage": 0,
                    "created": datetime.now().isoformat()
                },
                {
                    "id": 2,
                    "trigger": "morning routine",
                    "description": "Start the daily analysis workflow",
                    "category": "workflow",
                    "steps": [
                        "Check pre-market futures",
                        "Scan overnight news",
                        "Review earnings calendar",
                        "Check analyst upgrades/downgrades"
                    ],
                    "usage": 0,
                    "created": datetime.now().isoformat()
                },
                {
                    "id": 3,
                    "trigger": "what's moving",
                    "description": "Quick summary of biggest market movers",
                    "category": "query",
                    "steps": [
                        "Get top gainers",
                        "Get top losers",
                        "Check sector performance"
                    ],
                    "usage": 0,
                    "created": datetime.now().isoformat()
                }
            ]
            self.save_shortcuts()
    
    def save_shortcuts(self):
        """Save shortcuts to JSON file."""
        with open(self.shortcuts_file, 'w') as f:
            json.dump(self.shortcuts, f, indent=2)
    
    def load_usage_log(self):
        """Load usage log for analytics."""
        if USAGE_LOG_FILE.exists():
            with open(USAGE_LOG_FILE, 'r') as f:
                self.usage_log = json.load(f)
        else:
            self.usage_log = {"events": [], "daily_counts": {}}
    
    def save_usage_log(self):
        """Save usage log."""
        with open(USAGE_LOG_FILE, 'w') as f:
            json.dump(self.usage_log, f, indent=2)
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for matching."""
        # Lowercase and remove extra whitespace
        text = text.lower().strip()
        text = re.sub(r'\s+', ' ', text)
        # Remove common filler words
        fillers = ['please', 'can you', 'could you', 'hey', 'um', 'uh', 'like']
        for filler in fillers:
            text = text.replace(filler, '')
        return text.strip()
    
    def match(self, transcript: str) -> Optional[Dict]:
        """
        Match a voice transcript to a shortcut.
        
        Returns the matched shortcut or None if no match found.
        Uses fuzzy matching to handle variations.
        """
        normalized = self.normalize_text(transcript)
        
        best_match = None
        best_score = 0
        
        for shortcut in self.shortcuts:
            trigger = self.normalize_text(shortcut['trigger'])
            
            # Exact match
            if trigger in normalized:
                score = len(trigger) / len(normalized) if normalized else 0
                if score > best_score:
                    best_score = score
                    best_match = shortcut
            
            # Partial match (80% of words)
            trigger_words = set(trigger.split())
            transcript_words = set(normalized.split())
            if trigger_words:
                overlap = len(trigger_words & transcript_words) / len(trigger_words)
                if overlap >= 0.8 and overlap > best_score:
                    best_score = overlap
                    best_match = shortcut
        
        return best_match
    
    def execute(self, shortcut: Dict, context: Dict = None) -> Dict:
        """
        Execute a shortcut workflow.
        
        Returns execution result with status and step outputs.
        """
        result = {
            "shortcut_id": shortcut['id'],
            "trigger": shortcut['trigger'],
            "status": "success",
            "steps_completed": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # Log usage
        self.log_usage(shortcut['id'])
        
        # Execute each step
        for i, step in enumerate(shortcut['steps']):
            step_result = {
                "step": i + 1,
                "action": step,
                "status": "completed",
                "output": f"Executed: {step}"
            }
            result["steps_completed"].append(step_result)
            
            # In a real implementation, this would dispatch to actual handlers
            # based on the step content
        
        return result
    
    def log_usage(self, shortcut_id: int):
        """Log shortcut usage for analytics."""
        # Update shortcut usage count
        for shortcut in self.shortcuts:
            if shortcut['id'] == shortcut_id:
                shortcut['usage'] = shortcut.get('usage', 0) + 1
                break
        self.save_shortcuts()
        
        # Log event
        today = datetime.now().strftime('%Y-%m-%d')
        event = {
            "shortcut_id": shortcut_id,
            "timestamp": datetime.now().isoformat()
        }
        self.usage_log["events"].append(event)
        
        # Update daily count
        if today not in self.usage_log["daily_counts"]:
            self.usage_log["daily_counts"][today] = {}
        if str(shortcut_id) not in self.usage_log["daily_counts"][today]:
            self.usage_log["daily_counts"][today][str(shortcut_id)] = 0
        self.usage_log["daily_counts"][today][str(shortcut_id)] += 1
        
        self.save_usage_log()
    
    def add_shortcut(self, trigger: str, description: str, steps: List[str], 
                     category: str = "custom") -> Dict:
        """Add a new shortcut."""
        new_id = max([s['id'] for s in self.shortcuts], default=0) + 1
        shortcut = {
            "id": new_id,
            "trigger": trigger,
            "description": description,
            "category": category,
            "steps": steps,
            "usage": 0,
            "created": datetime.now().isoformat()
        }
        self.shortcuts.append(shortcut)
        self.save_shortcuts()
        return shortcut
    
    def update_shortcut(self, shortcut_id: int, **kwargs) -> Optional[Dict]:
        """Update an existing shortcut."""
        for shortcut in self.shortcuts:
            if shortcut['id'] == shortcut_id:
                for key, value in kwargs.items():
                    if key in ['trigger', 'description', 'steps', 'category']:
                        shortcut[key] = value
                self.save_shortcuts()
                return shortcut
        return None
    
    def delete_shortcut(self, shortcut_id: int) -> bool:
        """Delete a shortcut."""
        original_len = len(self.shortcuts)
        self.shortcuts = [s for s in self.shortcuts if s['id'] != shortcut_id]
        if len(self.shortcuts) < original_len:
            self.save_shortcuts()
            return True
        return False
    
    def get_stats(self) -> Dict:
        """Get usage statistics."""
        total_usage = sum(s.get('usage', 0) for s in self.shortcuts)
        top_used = sorted(self.shortcuts, key=lambda x: x.get('usage', 0), reverse=True)[:5]
        
        category_counts = {}
        for s in self.shortcuts:
            cat = s.get('category', 'custom')
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        return {
            "total_shortcuts": len(self.shortcuts),
            "total_usage": total_usage,
            "top_used": top_used,
            "category_counts": category_counts,
            "recent_events": self.usage_log.get("events", [])[-10:]
        }
    
    def learn_from_usage(self, transcript: str, actions_taken: List[str]):
        """
        Learn new shortcuts from repeated user patterns.
        
        If a user frequently says the same thing and takes the same actions,
        suggest creating a shortcut.
        """
        # This would track patterns over time and suggest new shortcuts
        # Implementation would require a pattern database
        pass


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Voice Shortcut Engine")
    parser.add_argument("command", choices=["list", "match", "add", "stats", "execute"],
                        help="Command to run")
    parser.add_argument("--transcript", "-t", help="Voice transcript to match")
    parser.add_argument("--trigger", help="Trigger phrase for new shortcut")
    parser.add_argument("--description", "-d", help="Description for new shortcut")
    parser.add_argument("--steps", "-s", nargs="+", help="Workflow steps")
    parser.add_argument("--category", "-c", default="custom", help="Category")
    
    args = parser.parse_args()
    
    engine = ShortcutEngine()
    
    if args.command == "list":
        print(f"\n{'='*60}")
        print("VOICE SHORTCUTS")
        print(f"{'='*60}\n")
        for s in engine.shortcuts:
            print(f"[*] \"{s['trigger']}\"")
            print(f"    Category: {s['category']} | Usage: {s.get('usage', 0)}")
            print(f"    Steps: {len(s['steps'])}")
            for i, step in enumerate(s['steps'], 1):
                print(f"      {i}. {step}")
            print()
    
    elif args.command == "match":
        if not args.transcript:
            print("Error: --transcript required")
            exit(1)
        
        match = engine.match(args.transcript)
        if match:
            print(f"\n[MATCHED] \"{match['trigger']}\"")
            print(f"   {match['description']}")
            print("\n   Workflow steps:")
            for i, step in enumerate(match['steps'], 1):
                print(f"     {i}. {step}")
        else:
            print(f"\n[NO MATCH] for: \"{args.transcript}\"")
    
    elif args.command == "execute":
        if not args.transcript:
            print("Error: --transcript required")
            exit(1)
        
        match = engine.match(args.transcript)
        if match:
            result = engine.execute(match)
            print(f"\n[EXECUTING] \"{match['trigger']}\"")
            for step in result['steps_completed']:
                print(f"   > Step {step['step']}: {step['action']}")
            print(f"\n[DONE] Completed at {result['timestamp']}")
        else:
            print(f"\n[NO MATCH] for: \"{args.transcript}\"")
    
    elif args.command == "add":
        if not args.trigger or not args.steps:
            print("Error: --trigger and --steps required")
            exit(1)
        
        shortcut = engine.add_shortcut(
            trigger=args.trigger,
            description=args.description or "",
            steps=args.steps,
            category=args.category
        )
        print(f"\n[CREATED] shortcut #{shortcut['id']}: \"{shortcut['trigger']}\"")
    
    elif args.command == "stats":
        stats = engine.get_stats()
        print(f"\n{'='*60}")
        print("SHORTCUT STATISTICS")
        print(f"{'='*60}\n")
        print(f"Total shortcuts: {stats['total_shortcuts']}")
        print(f"Total usage: {stats['total_usage']}")
        print(f"\nCategories:")
        for cat, count in stats['category_counts'].items():
            print(f"  • {cat}: {count}")
        print(f"\nTop used:")
        for s in stats['top_used']:
            print(f"  • \"{s['trigger']}\" ({s.get('usage', 0)} uses)")
