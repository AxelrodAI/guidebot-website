#!/usr/bin/env python3
"""
Proactive Email Drafts Engine
Auto-draft responses based on context and patterns.
Built by PM3 (Backend/Data Builder)
"""

import argparse
import json
import os
import re
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter
from typing import Dict, List, Optional, Tuple

DATA_DIR = Path(__file__).parent / "data"
EMAILS_FILE = DATA_DIR / "emails.json"
DRAFTS_FILE = DATA_DIR / "drafts.json"
PATTERNS_FILE = DATA_DIR / "patterns.json"
STYLE_FILE = DATA_DIR / "style_profile.json"
CONFIG_FILE = DATA_DIR / "config.json"


def ensure_data_dir():
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_json(filepath: Path, default=None):
    """Load JSON file or return default."""
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default if default is not None else {}


def save_json(filepath: Path, data):
    """Save data to JSON file."""
    ensure_data_dir()
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)


def get_config() -> Dict:
    """Get configuration with defaults."""
    config = load_json(CONFIG_FILE, {})
    defaults = {
        "auto_draft_enabled": True,
        "min_priority_for_draft": 3,  # 1-5 scale
        "max_drafts_per_day": 50,
        "response_tone": "professional",  # professional, casual, formal
        "include_greeting": True,
        "include_signature": True,
        "signature": "Best regards",
        "user_name": "User",
        "urgency_keywords": ["urgent", "asap", "immediately", "critical", "deadline", "eod", "end of day"],
        "question_keywords": ["?", "could you", "can you", "would you", "please", "need", "require"],
        "meeting_keywords": ["meeting", "calendar", "schedule", "call", "sync", "discuss"],
        "action_keywords": ["action", "task", "todo", "review", "approve", "sign", "submit"]
    }
    for k, v in defaults.items():
        if k not in config:
            config[k] = v
    return config


def generate_email_id(email: Dict) -> str:
    """Generate unique ID for email."""
    content = f"{email.get('from', '')}{email.get('subject', '')}{email.get('received', '')}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


def analyze_email_context(email: Dict, config: Dict) -> Dict:
    """Analyze email for context signals."""
    subject = email.get('subject', '').lower()
    body = email.get('body', '').lower()
    combined = f"{subject} {body}"
    
    # Urgency detection
    urgency_score = 0
    urgency_signals = []
    for kw in config['urgency_keywords']:
        if kw in combined:
            urgency_score += 2
            urgency_signals.append(kw)
    
    # Question detection
    questions = []
    sentences = re.split(r'[.!?]', body)
    for sent in sentences:
        sent = sent.strip()
        if '?' in sent or any(kw in sent.lower() for kw in config['question_keywords']):
            if len(sent) > 10:
                questions.append(sent)
    
    # Meeting request detection
    is_meeting_request = any(kw in combined for kw in config['meeting_keywords'])
    
    # Action item detection
    action_items = []
    for kw in config['action_keywords']:
        if kw in combined:
            # Extract surrounding context
            for sent in sentences:
                if kw in sent.lower() and len(sent.strip()) > 5:
                    action_items.append(sent.strip())
    
    # Priority calculation (1-5)
    priority = 3  # default medium
    if urgency_score >= 4:
        priority = 5
    elif urgency_score >= 2:
        priority = 4
    if is_meeting_request:
        priority = max(priority, 4)
    if len(questions) > 2:
        priority = max(priority, 4)
    
    # Sentiment hints
    positive_words = ['thanks', 'great', 'appreciate', 'excellent', 'wonderful', 'good news']
    negative_words = ['issue', 'problem', 'concern', 'disappointed', 'urgent', 'fail', 'error']
    
    sentiment = "neutral"
    pos_count = sum(1 for w in positive_words if w in combined)
    neg_count = sum(1 for w in negative_words if w in combined)
    if pos_count > neg_count:
        sentiment = "positive"
    elif neg_count > pos_count:
        sentiment = "negative"
    
    return {
        "urgency_score": urgency_score,
        "urgency_signals": urgency_signals,
        "questions": questions[:5],  # max 5
        "is_meeting_request": is_meeting_request,
        "action_items": action_items[:5],
        "priority": priority,
        "sentiment": sentiment,
        "word_count": len(body.split()),
        "needs_response": priority >= 3 or len(questions) > 0 or is_meeting_request
    }


def get_style_profile() -> Dict:
    """Get user's writing style profile."""
    profile = load_json(STYLE_FILE, {})
    defaults = {
        "common_greetings": ["Hi", "Hello", "Hey"],
        "common_closings": ["Best", "Thanks", "Regards"],
        "avg_response_length": 100,
        "formality_level": 0.6,  # 0-1, higher = more formal
        "response_speed_hours": 4,
        "common_phrases": [],
        "samples_analyzed": 0
    }
    for k, v in defaults.items():
        if k not in profile:
            profile[k] = v
    return profile


def learn_from_response(original_email: Dict, response: Dict):
    """Learn from a user's actual response to update style profile."""
    profile = get_style_profile()
    response_body = response.get('body', '')
    
    # Extract greeting
    lines = response_body.split('\n')
    if lines and len(lines[0]) < 50:
        greeting = lines[0].strip().rstrip(',')
        if greeting and greeting not in profile['common_greetings']:
            profile['common_greetings'].append(greeting)
            profile['common_greetings'] = profile['common_greetings'][-10:]  # keep last 10
    
    # Extract closing
    for i in range(len(lines) - 1, max(len(lines) - 5, -1), -1):
        line = lines[i].strip()
        if line and len(line) < 30 and not line.endswith('?'):
            if line not in profile['common_closings']:
                profile['common_closings'].append(line)
                profile['common_closings'] = profile['common_closings'][-10:]
            break
    
    # Update average length
    word_count = len(response_body.split())
    samples = profile['samples_analyzed']
    profile['avg_response_length'] = (
        (profile['avg_response_length'] * samples + word_count) / (samples + 1)
    )
    profile['samples_analyzed'] = samples + 1
    
    save_json(STYLE_FILE, profile)
    return profile


def generate_draft_response(email: Dict, context: Dict, config: Dict, style: Dict) -> Dict:
    """Generate a draft response based on email context."""
    sender = email.get('from', 'there')
    sender_name = sender.split('@')[0].split('<')[0].strip().title()
    if '<' in sender:
        sender_name = sender.split('<')[0].strip()
    
    # Select greeting based on formality
    greetings = style.get('common_greetings', ['Hi'])
    greeting = greetings[0] if greetings else "Hi"
    if style['formality_level'] > 0.7:
        greeting = "Dear"
    
    # Build response body
    body_parts = []
    
    # Opening based on sentiment
    if context['sentiment'] == 'positive':
        body_parts.append("Thank you for reaching out!")
    elif context['sentiment'] == 'negative':
        body_parts.append("Thank you for bringing this to my attention.")
    else:
        body_parts.append("Thank you for your email.")
    
    # Address questions
    if context['questions']:
        if len(context['questions']) == 1:
            body_parts.append("\nRegarding your question:")
            body_parts.append(f"[ANSWER: {context['questions'][0][:100]}...]")
        else:
            body_parts.append(f"\nI'll address your {len(context['questions'])} questions:")
            for i, q in enumerate(context['questions'][:3], 1):
                body_parts.append(f"\n{i}. [ANSWER: {q[:80]}...]")
    
    # Handle meeting requests
    if context['is_meeting_request']:
        body_parts.append("\nRegarding the meeting request:")
        body_parts.append("[CONFIRM/PROPOSE_ALTERNATIVE: Check your calendar and respond]")
    
    # Handle action items
    if context['action_items']:
        body_parts.append("\nI've noted the following action items:")
        for item in context['action_items'][:3]:
            body_parts.append(f"• {item[:80]}")
        body_parts.append("[CONFIRM_ACTIONS: Review and confirm timeline]")
    
    # Urgency acknowledgment
    if context['urgency_score'] >= 4:
        body_parts.append("\nI understand this is urgent and will prioritize accordingly.")
    
    # Closing
    closings = style.get('common_closings', ['Best'])
    closing = closings[0] if closings else config.get('signature', 'Best regards')
    
    # Assemble draft
    draft_body = f"{greeting} {sender_name},\n\n"
    draft_body += "\n".join(body_parts)
    draft_body += f"\n\n{closing},\n{config.get('user_name', 'User')}"
    
    return {
        "id": f"draft_{generate_email_id(email)}",
        "in_reply_to": email.get('id', generate_email_id(email)),
        "to": email.get('from', ''),
        "subject": f"Re: {email.get('subject', '')}",
        "body": draft_body,
        "context": context,
        "generated_at": datetime.now().isoformat(),
        "status": "draft",  # draft, edited, sent, discarded
        "confidence": calculate_confidence(context),
        "placeholders": extract_placeholders(draft_body)
    }


def calculate_confidence(context: Dict) -> float:
    """Calculate confidence score for draft (0-1)."""
    confidence = 0.5  # base
    
    # Higher confidence for clear context
    if context['questions']:
        confidence += 0.1
    if context['is_meeting_request']:
        confidence += 0.15
    if context['action_items']:
        confidence += 0.1
    if context['sentiment'] != 'neutral':
        confidence += 0.05
    
    # Lower confidence for very long emails (complex)
    if context['word_count'] > 500:
        confidence -= 0.2
    elif context['word_count'] > 300:
        confidence -= 0.1
    
    return max(0.1, min(0.95, confidence))


def extract_placeholders(body: str) -> List[str]:
    """Extract placeholder markers that need user input."""
    placeholders = re.findall(r'\[([A-Z_]+:[^\]]+)\]', body)
    return placeholders


# ============ CLI Commands ============

def cmd_analyze(args):
    """Analyze an email for context."""
    config = get_config()
    
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            email = json.load(f)
    else:
        # Interactive mode
        print("Enter email details (Ctrl+D or empty line to finish body):")
        email = {
            'from': input("From: "),
            'subject': input("Subject: "),
            'body': ""
        }
        print("Body (empty line to finish):")
        lines = []
        while True:
            try:
                line = input()
                if line == "":
                    break
                lines.append(line)
            except EOFError:
                break
        email['body'] = "\n".join(lines)
    
    context = analyze_email_context(email, config)
    
    if args.json:
        print(json.dumps(context, indent=2))
    else:
        print("\n📧 Email Analysis")
        print("=" * 50)
        print(f"Priority: {'⭐' * context['priority']} ({context['priority']}/5)")
        print(f"Sentiment: {context['sentiment']}")
        print(f"Urgency Score: {context['urgency_score']}")
        if context['urgency_signals']:
            print(f"Urgency Signals: {', '.join(context['urgency_signals'])}")
        print(f"Meeting Request: {'Yes' if context['is_meeting_request'] else 'No'}")
        print(f"Questions Found: {len(context['questions'])}")
        if context['questions']:
            for i, q in enumerate(context['questions'][:3], 1):
                print(f"  {i}. {q[:60]}...")
        print(f"Action Items: {len(context['action_items'])}")
        if context['action_items']:
            for item in context['action_items'][:3]:
                print(f"  • {item[:60]}")
        print(f"Needs Response: {'Yes' if context['needs_response'] else 'Maybe not'}")


def cmd_draft(args):
    """Generate a draft response."""
    config = get_config()
    style = get_style_profile()
    
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            email = json.load(f)
    elif args.email_id:
        emails = load_json(EMAILS_FILE, {"emails": []})
        email = next((e for e in emails.get('emails', []) if e.get('id') == args.email_id), None)
        if not email:
            print(f"❌ Email {args.email_id} not found")
            return
    else:
        # Interactive mode
        print("Enter email to respond to:")
        email = {
            'from': input("From: "),
            'subject': input("Subject: "),
            'body': ""
        }
        print("Body (empty line to finish):")
        lines = []
        while True:
            try:
                line = input()
                if line == "":
                    break
                lines.append(line)
            except EOFError:
                break
        email['body'] = "\n".join(lines)
    
    context = analyze_email_context(email, config)
    draft = generate_draft_response(email, context, config, style)
    
    # Save draft
    drafts = load_json(DRAFTS_FILE, {"drafts": []})
    drafts['drafts'].append(draft)
    save_json(DRAFTS_FILE, drafts)
    
    if args.json:
        print(json.dumps(draft, indent=2))
    else:
        print("\n📝 Draft Response Generated")
        print("=" * 50)
        print(f"Draft ID: {draft['id']}")
        print(f"To: {draft['to']}")
        print(f"Subject: {draft['subject']}")
        print(f"Confidence: {draft['confidence']:.0%}")
        print("-" * 50)
        print(draft['body'])
        print("-" * 50)
        if draft['placeholders']:
            print("\n⚠️  Placeholders to fill in:")
            for ph in draft['placeholders']:
                print(f"  • {ph}")


def cmd_list(args):
    """List drafts or emails."""
    if args.type == 'drafts':
        drafts = load_json(DRAFTS_FILE, {"drafts": []})
        items = drafts.get('drafts', [])
        if args.status:
            items = [d for d in items if d.get('status') == args.status]
    else:
        emails = load_json(EMAILS_FILE, {"emails": []})
        items = emails.get('emails', [])
    
    if not items:
        print(f"No {args.type} found.")
        return
    
    # Sort by date
    items = sorted(items, key=lambda x: x.get('generated_at', x.get('received', '')), reverse=True)
    
    if args.limit:
        items = items[:args.limit]
    
    if args.json:
        print(json.dumps(items, indent=2))
    else:
        print(f"\n📋 {args.type.title()} ({len(items)} items)")
        print("=" * 60)
        for item in items:
            if args.type == 'drafts':
                print(f"ID: {item['id']}")
                print(f"  To: {item['to'][:40]}")
                print(f"  Subject: {item['subject'][:50]}")
                print(f"  Status: {item['status']} | Confidence: {item.get('confidence', 0):.0%}")
                print(f"  Generated: {item['generated_at']}")
            else:
                print(f"ID: {item.get('id', 'N/A')}")
                print(f"  From: {item.get('from', 'N/A')[:40]}")
                print(f"  Subject: {item.get('subject', 'N/A')[:50]}")
                print(f"  Received: {item.get('received', 'N/A')}")
            print()


def cmd_import(args):
    """Import emails for drafting."""
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        print("Enter email JSON (Ctrl+D when done):")
        import sys
        data = json.load(sys.stdin)
    
    emails = load_json(EMAILS_FILE, {"emails": []})
    
    # Handle single email or list
    new_emails = data if isinstance(data, list) else [data]
    
    count = 0
    for email in new_emails:
        if 'id' not in email:
            email['id'] = generate_email_id(email)
        if 'received' not in email:
            email['received'] = datetime.now().isoformat()
        
        # Check for duplicates
        existing_ids = {e.get('id') for e in emails['emails']}
        if email['id'] not in existing_ids:
            emails['emails'].append(email)
            count += 1
    
    save_json(EMAILS_FILE, emails)
    print(f"✅ Imported {count} email(s)")


def cmd_batch_draft(args):
    """Generate drafts for all pending emails."""
    config = get_config()
    style = get_style_profile()
    emails = load_json(EMAILS_FILE, {"emails": []})
    drafts = load_json(DRAFTS_FILE, {"drafts": []})
    
    # Get emails that don't have drafts yet
    existing_draft_refs = {d.get('in_reply_to') for d in drafts.get('drafts', [])}
    pending = [e for e in emails.get('emails', []) 
               if e.get('id') not in existing_draft_refs]
    
    if args.min_priority:
        pending = [e for e in pending 
                   if analyze_email_context(e, config)['priority'] >= args.min_priority]
    
    if args.limit:
        pending = pending[:args.limit]
    
    if not pending:
        print("No pending emails to draft.")
        return
    
    generated = 0
    for email in pending:
        context = analyze_email_context(email, config)
        if context['needs_response']:
            draft = generate_draft_response(email, context, config, style)
            drafts['drafts'].append(draft)
            generated += 1
            if not args.quiet:
                print(f"📝 Draft: {draft['subject'][:50]} (conf: {draft['confidence']:.0%})")
    
    save_json(DRAFTS_FILE, drafts)
    print(f"\n✅ Generated {generated} draft(s)")


def cmd_edit(args):
    """Edit a draft."""
    drafts = load_json(DRAFTS_FILE, {"drafts": []})
    draft = next((d for d in drafts.get('drafts', []) if d.get('id') == args.draft_id), None)
    
    if not draft:
        print(f"❌ Draft {args.draft_id} not found")
        return
    
    if args.body:
        draft['body'] = args.body
    if args.status:
        draft['status'] = args.status
    
    draft['edited_at'] = datetime.now().isoformat()
    save_json(DRAFTS_FILE, drafts)
    print(f"✅ Draft {args.draft_id} updated")


def cmd_discard(args):
    """Discard a draft."""
    drafts = load_json(DRAFTS_FILE, {"drafts": []})
    
    if args.all:
        count = len(drafts.get('drafts', []))
        drafts['drafts'] = []
        save_json(DRAFTS_FILE, drafts)
        print(f"🗑️  Discarded all {count} drafts")
        return
    
    original_count = len(drafts.get('drafts', []))
    drafts['drafts'] = [d for d in drafts.get('drafts', []) if d.get('id') != args.draft_id]
    
    if len(drafts['drafts']) < original_count:
        save_json(DRAFTS_FILE, drafts)
        print(f"🗑️  Discarded draft {args.draft_id}")
    else:
        print(f"❌ Draft {args.draft_id} not found")


def cmd_learn(args):
    """Learn from a sent response."""
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            response = json.load(f)
    else:
        print("Enter the response you sent:")
        response = {'body': ''}
        print("Body (empty line to finish):")
        lines = []
        while True:
            try:
                line = input()
                if line == "":
                    break
                lines.append(line)
            except EOFError:
                break
        response['body'] = "\n".join(lines)
    
    # Get original email if provided
    original = {}
    if args.original_id:
        emails = load_json(EMAILS_FILE, {"emails": []})
        original = next((e for e in emails.get('emails', []) if e.get('id') == args.original_id), {})
    
    profile = learn_from_response(original, response)
    print(f"✅ Learned from response. Total samples: {profile['samples_analyzed']}")
    print(f"   Avg response length: {profile['avg_response_length']:.0f} words")


def cmd_style(args):
    """View or update style profile."""
    style = get_style_profile()
    
    if args.set_formality is not None:
        style['formality_level'] = max(0, min(1, args.set_formality))
        save_json(STYLE_FILE, style)
        print(f"✅ Formality level set to {style['formality_level']:.1f}")
        return
    
    if args.json:
        print(json.dumps(style, indent=2))
    else:
        print("\n✍️  Writing Style Profile")
        print("=" * 50)
        print(f"Samples analyzed: {style['samples_analyzed']}")
        print(f"Avg response length: {style['avg_response_length']:.0f} words")
        print(f"Formality level: {style['formality_level']:.1f} (0=casual, 1=formal)")
        print(f"Common greetings: {', '.join(style['common_greetings'][:5])}")
        print(f"Common closings: {', '.join(style['common_closings'][:5])}")


def cmd_config(args):
    """View or update configuration."""
    config = get_config()
    
    if args.key and args.value:
        # Try to parse JSON for complex values
        try:
            value = json.loads(args.value)
        except:
            value = args.value
        config[args.key] = value
        save_json(CONFIG_FILE, config)
        print(f"✅ Set {args.key} = {value}")
        return
    
    if args.json:
        print(json.dumps(config, indent=2))
    else:
        print("\n⚙️  Configuration")
        print("=" * 50)
        for k, v in config.items():
            if isinstance(v, list):
                print(f"{k}: [{', '.join(str(x) for x in v[:3])}...]")
            else:
                print(f"{k}: {v}")


def cmd_stats(args):
    """Show drafting statistics."""
    drafts = load_json(DRAFTS_FILE, {"drafts": []})
    emails = load_json(EMAILS_FILE, {"emails": []})
    style = get_style_profile()
    
    all_drafts = drafts.get('drafts', [])
    
    # Stats
    status_counts = Counter(d.get('status') for d in all_drafts)
    avg_confidence = sum(d.get('confidence', 0) for d in all_drafts) / len(all_drafts) if all_drafts else 0
    
    # Recent activity
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    recent_drafts = [d for d in all_drafts if d.get('generated_at', '') > week_ago]
    
    print("\n📊 Email Drafting Statistics")
    print("=" * 50)
    print(f"Total emails: {len(emails.get('emails', []))}")
    print(f"Total drafts: {len(all_drafts)}")
    print(f"Drafts this week: {len(recent_drafts)}")
    print(f"Average confidence: {avg_confidence:.0%}")
    print(f"\nDraft status breakdown:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")
    print(f"\nStyle samples: {style['samples_analyzed']}")


def main():
    parser = argparse.ArgumentParser(
        description="Proactive Email Drafts - Auto-draft responses based on context",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s analyze -f email.json         Analyze an email file
  %(prog)s draft -f email.json           Generate draft response
  %(prog)s batch --limit 10              Draft responses for 10 emails
  %(prog)s list drafts                   List all drafts
  %(prog)s edit DRAFT_ID --status sent   Mark draft as sent
  %(prog)s learn -f response.json        Learn from sent response
  %(prog)s style                         View writing style profile
  %(prog)s stats                         View statistics
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # analyze
    p_analyze = subparsers.add_parser('analyze', help='Analyze email for context')
    p_analyze.add_argument('-f', '--file', help='Email JSON file')
    p_analyze.add_argument('--json', action='store_true', help='JSON output')
    
    # draft
    p_draft = subparsers.add_parser('draft', help='Generate draft response')
    p_draft.add_argument('-f', '--file', help='Email JSON file')
    p_draft.add_argument('-e', '--email-id', help='Email ID from storage')
    p_draft.add_argument('--json', action='store_true', help='JSON output')
    
    # list
    p_list = subparsers.add_parser('list', help='List drafts or emails')
    p_list.add_argument('type', choices=['drafts', 'emails'], help='What to list')
    p_list.add_argument('--status', help='Filter by status')
    p_list.add_argument('--limit', type=int, help='Limit results')
    p_list.add_argument('--json', action='store_true', help='JSON output')
    
    # import
    p_import = subparsers.add_parser('import', help='Import emails')
    p_import.add_argument('-f', '--file', help='JSON file with emails')
    
    # batch
    p_batch = subparsers.add_parser('batch', help='Batch generate drafts')
    p_batch.add_argument('--min-priority', type=int, help='Minimum priority (1-5)')
    p_batch.add_argument('--limit', type=int, help='Max drafts to generate')
    p_batch.add_argument('-q', '--quiet', action='store_true', help='Quiet output')
    
    # edit
    p_edit = subparsers.add_parser('edit', help='Edit a draft')
    p_edit.add_argument('draft_id', help='Draft ID')
    p_edit.add_argument('--body', help='New body text')
    p_edit.add_argument('--status', choices=['draft', 'edited', 'sent', 'discarded'])
    
    # discard
    p_discard = subparsers.add_parser('discard', help='Discard draft(s)')
    p_discard.add_argument('draft_id', nargs='?', help='Draft ID')
    p_discard.add_argument('--all', action='store_true', help='Discard all')
    
    # learn
    p_learn = subparsers.add_parser('learn', help='Learn from sent response')
    p_learn.add_argument('-f', '--file', help='Response JSON file')
    p_learn.add_argument('-o', '--original-id', help='Original email ID')
    
    # style
    p_style = subparsers.add_parser('style', help='View/update style profile')
    p_style.add_argument('--set-formality', type=float, help='Set formality (0-1)')
    p_style.add_argument('--json', action='store_true', help='JSON output')
    
    # config
    p_config = subparsers.add_parser('config', help='View/update config')
    p_config.add_argument('--key', help='Config key to set')
    p_config.add_argument('--value', help='Value to set')
    p_config.add_argument('--json', action='store_true', help='JSON output')
    
    # stats
    p_stats = subparsers.add_parser('stats', help='View statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    commands = {
        'analyze': cmd_analyze,
        'draft': cmd_draft,
        'list': cmd_list,
        'import': cmd_import,
        'batch': cmd_batch_draft,
        'edit': cmd_edit,
        'discard': cmd_discard,
        'learn': cmd_learn,
        'style': cmd_style,
        'config': cmd_config,
        'stats': cmd_stats
    }
    
    commands[args.command](args)


if __name__ == '__main__':
    main()
