#!/usr/bin/env python3
"""
Smart Meeting Prep - Backend Engine
Gathers attendee info, notes, and emails before meetings.

Usage:
    python meeting_prep.py upcoming              # List upcoming meetings
    python meeting_prep.py prep -m <meeting_id>  # Generate prep for meeting
    python meeting_prep.py attendees -m <id>     # Get attendee intel
    python meeting_prep.py search -q "topic"     # Search related docs/emails
    python meeting_prep.py briefing -m <id>      # Generate AI briefing
    python meeting_prep.py export -m <id>        # Export prep kit to JSON
"""

import argparse
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import hashlib

# Storage paths
DATA_DIR = Path(__file__).parent / "data"
MEETINGS_FILE = DATA_DIR / "meetings.json"
CONTACTS_FILE = DATA_DIR / "contacts.json"
HISTORY_FILE = DATA_DIR / "meeting_history.json"


def ensure_data_dir():
    """Create data directory if needed."""
    DATA_DIR.mkdir(exist_ok=True)


def load_json(path: Path, default=None):
    """Load JSON file or return default."""
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return default if default is not None else {}


def save_json(path: Path, data):
    """Save data to JSON file."""
    ensure_data_dir()
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


# Sample data for demonstration
SAMPLE_MEETINGS = [
    {
        "id": "mtg_001",
        "title": "Q4 Planning Review",
        "datetime": (datetime.now() + timedelta(hours=2)).isoformat(),
        "duration_min": 60,
        "attendees": ["sarah.chen@company.com", "mike.ross@company.com", "lisa.park@company.com"],
        "location": "Conference Room A / Zoom",
        "agenda": ["Review Q4 OKRs", "Discuss budget allocation", "Align on priorities"],
        "type": "review"
    },
    {
        "id": "mtg_002",
        "title": "1:1 with Alex Thompson",
        "datetime": (datetime.now() + timedelta(hours=5)).isoformat(),
        "duration_min": 30,
        "attendees": ["alex.thompson@company.com"],
        "location": "Office",
        "agenda": ["Performance review", "Career development", "Project updates"],
        "type": "1on1"
    },
    {
        "id": "mtg_003",
        "title": "Product Roadmap Discussion",
        "datetime": (datetime.now() + timedelta(days=1, hours=2)).isoformat(),
        "duration_min": 90,
        "attendees": ["product-team@company.com", "eng-leads@company.com"],
        "location": "Zoom",
        "agenda": ["Review roadmap progress", "Q1 planning", "Resource allocation"],
        "type": "planning"
    },
    {
        "id": "mtg_004",
        "title": "Investor Update Call",
        "datetime": (datetime.now() + timedelta(days=1, hours=7)).isoformat(),
        "duration_min": 45,
        "attendees": ["john.smith@acmevc.com", "board@company.com"],
        "location": "Zoom",
        "agenda": ["Quarterly metrics", "Growth update", "Funding discussion"],
        "type": "external"
    }
]

SAMPLE_CONTACTS = {
    "sarah.chen@company.com": {
        "name": "Sarah Chen",
        "role": "VP of Engineering",
        "department": "Engineering",
        "last_interaction": "3 days ago",
        "notes": "Discussed infrastructure budget concerns. Prefers data-driven decisions.",
        "communication_style": "Direct, detail-oriented",
        "linkedin": "linkedin.com/in/sarahchen"
    },
    "mike.ross@company.com": {
        "name": "Mike Ross",
        "role": "Product Manager",
        "department": "Product",
        "last_interaction": "1 week ago",
        "notes": "Sent feature spec for review. Waiting for feedback on API design.",
        "communication_style": "Collaborative, visual thinker",
        "linkedin": "linkedin.com/in/mikeross"
    },
    "lisa.park@company.com": {
        "name": "Lisa Park",
        "role": "Design Lead",
        "department": "Design",
        "last_interaction": "2 weeks ago",
        "notes": "New to team (2 months). Previously at Stripe. Strong UX background.",
        "communication_style": "Creative, user-focused",
        "linkedin": "linkedin.com/in/lisapark"
    },
    "alex.thompson@company.com": {
        "name": "Alex Thompson",
        "role": "Senior Engineer",
        "department": "Engineering",
        "last_interaction": "Yesterday",
        "notes": "Performance review coming up. Working on Auth system refactor.",
        "communication_style": "Technical, thoughtful",
        "linkedin": "linkedin.com/in/alexthompson"
    },
    "john.smith@acmevc.com": {
        "name": "John Smith",
        "role": "Partner",
        "department": "Acme VC",
        "last_interaction": "Last month",
        "notes": "Board member since Series A. Focuses on growth metrics and unit economics.",
        "communication_style": "Strategic, metrics-focused",
        "linkedin": "linkedin.com/in/johnsmithvc"
    }
}

SAMPLE_EMAILS = [
    {
        "id": "email_001",
        "subject": "Re: Q4 Planning - Initial Thoughts",
        "from": "sarah.chen@company.com",
        "date": (datetime.now() - timedelta(days=2)).isoformat(),
        "preview": "I think we should prioritize the API redesign given customer feedback...",
        "tags": ["planning", "q4", "api"]
    },
    {
        "id": "email_002",
        "subject": "Updated timeline for infrastructure work",
        "from": "mike.ross@company.com",
        "date": (datetime.now() - timedelta(days=3)).isoformat(),
        "preview": "Given the recent discussions, here is the revised timeline for the infra...",
        "tags": ["infrastructure", "timeline"]
    },
    {
        "id": "email_003",
        "subject": "Design review feedback",
        "from": "lisa.park@company.com",
        "date": (datetime.now() - timedelta(days=5)).isoformat(),
        "preview": "Thanks for the feedback on the mockups. I have incorporated the changes...",
        "tags": ["design", "review"]
    },
    {
        "id": "email_004",
        "subject": "FW: Customer feedback summary",
        "from": "support@company.com",
        "date": (datetime.now() - timedelta(days=1)).isoformat(),
        "preview": "Sharing the latest NPS results and key themes from customer interviews...",
        "tags": ["customer", "feedback", "nps"]
    }
]

SAMPLE_DOCUMENTS = [
    {"name": "Q4 OKRs Spreadsheet", "type": "spreadsheet", "updated": "2 days ago", "relevance": 0.95},
    {"name": "Engineering Roadmap 2024", "type": "document", "updated": "1 week ago", "relevance": 0.88},
    {"name": "Performance Metrics Dashboard", "type": "dashboard", "updated": "live", "relevance": 0.92},
    {"name": "Last Meeting Notes", "type": "notes", "updated": "Nov 15, 2024", "relevance": 0.85},
    {"name": "Budget Allocation Doc", "type": "spreadsheet", "updated": "yesterday", "relevance": 0.90},
    {"name": "Team Goals Tracker", "type": "tracker", "updated": "today", "relevance": 0.87}
]


def get_upcoming_meetings(days: int = 7) -> List[Dict]:
    """Get meetings in the next N days."""
    # In production, this would integrate with Google Calendar, Outlook, etc.
    return SAMPLE_MEETINGS


def get_attendee_intel(email: str) -> Optional[Dict]:
    """Get intelligence on a meeting attendee."""
    contact = SAMPLE_CONTACTS.get(email)
    if contact:
        return {
            **contact,
            "email": email,
            "recent_emails": [e for e in SAMPLE_EMAILS if e["from"] == email][:3]
        }
    return None


def get_related_emails(meeting_id: str, keywords: List[str] = None) -> List[Dict]:
    """Find emails related to a meeting topic."""
    # In production, this would search email via API
    return SAMPLE_EMAILS[:4]


def get_related_documents(meeting_id: str) -> List[Dict]:
    """Find documents related to a meeting."""
    # In production, this would search Drive, Dropbox, etc.
    return SAMPLE_DOCUMENTS


def generate_briefing(meeting: Dict, attendees: List[Dict], emails: List[Dict], docs: List[Dict]) -> str:
    """Generate an AI briefing for the meeting."""
    briefing = f"""
╔══════════════════════════════════════════════════════════════════╗
║                    🤖 AI-GENERATED BRIEFING                       ║
╚══════════════════════════════════════════════════════════════════╝

📋 MEETING: {meeting['title']}
⏰ TIME: {meeting['datetime'][:16].replace('T', ' ')}
📍 LOCATION: {meeting['location']}
⏱️  DURATION: {meeting['duration_min']} minutes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👥 ATTENDEES ({len(attendees)}):
"""
    for att in attendees:
        briefing += f"""
   • {att['name']} - {att['role']}
     Last interaction: {att.get('last_interaction', 'Unknown')}
     Style: {att.get('communication_style', 'Unknown')}
     Context: {att.get('notes', 'No notes')}
"""

    briefing += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 AGENDA:
"""
    for i, item in enumerate(meeting.get('agenda', []), 1):
        briefing += f"   {i}. {item}\n"

    briefing += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📧 RECENT RELATED EMAILS:
"""
    for email in emails[:4]:
        briefing += f"""   • "{email['subject']}"
     From: {email['from']} | {email['date'][:10]}
"""

    briefing += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 RELEVANT DOCUMENTS:
"""
    for doc in docs[:5]:
        briefing += f"   • {doc['name']} (updated {doc['updated']})\n"

    briefing += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 SUGGESTED TALKING POINTS:
   1. Start with a quick status round (5 min)
   2. Deep dive on top priorities from agenda
   3. Identify blockers and assign owners
   4. Align on next steps and timeline

🎯 POTENTIAL QUESTIONS TO EXPECT:
   • "What's the realistic timeline for key deliverables?"
   • "How do we handle resource constraints?"
   • "What are the biggest risks to our plan?"

✅ PRE-MEETING CHECKLIST:
   [ ] Review all linked documents
   [ ] Check recent email threads
   [ ] Prepare data for key metrics
   [ ] Have backup plan for contentious topics
   [ ] Test A/V if remote meeting

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
    return briefing


def calculate_prep_score(meeting: Dict, attendees: List[Dict], emails: List[Dict], docs: List[Dict]) -> Dict:
    """Calculate a preparation score."""
    scores = {
        "attendees_researched": min(len(attendees) / max(len(meeting.get('attendees', [])), 1), 1.0),
        "docs_gathered": min(len(docs) / 5, 1.0),
        "emails_reviewed": min(len(emails) / 4, 1.0),
        "agenda_ready": 1.0 if meeting.get('agenda') else 0.0
    }
    
    overall = sum(scores.values()) / len(scores) * 100
    
    return {
        "overall_score": round(overall),
        "components": scores,
        "status": "Well Prepared" if overall >= 80 else "Needs More Prep" if overall >= 50 else "Under Prepared"
    }


def cmd_upcoming(args):
    """List upcoming meetings."""
    meetings = get_upcoming_meetings(args.days)
    
    print("\n📅 UPCOMING MEETINGS")
    print("=" * 60)
    
    for m in meetings:
        dt = m['datetime'][:16].replace('T', ' ')
        print(f"\n🔹 {m['title']}")
        print(f"   ID: {m['id']}")
        print(f"   Time: {dt}")
        print(f"   Duration: {m['duration_min']} min")
        print(f"   Attendees: {', '.join(m['attendees'])}")
        print(f"   Type: {m['type']}")


def cmd_prep(args):
    """Generate full prep for a meeting."""
    meetings = get_upcoming_meetings()
    meeting = next((m for m in meetings if m['id'] == args.meeting_id), None)
    
    if not meeting:
        print(f"❌ Meeting not found: {args.meeting_id}")
        return
    
    # Gather intel
    attendees = [get_attendee_intel(email) for email in meeting.get('attendees', [])]
    attendees = [a for a in attendees if a]  # Filter None
    emails = get_related_emails(args.meeting_id)
    docs = get_related_documents(args.meeting_id)
    
    # Calculate prep score
    score = calculate_prep_score(meeting, attendees, emails, docs)
    
    print(f"\n🎯 MEETING PREP: {meeting['title']}")
    print("=" * 60)
    print(f"\n📊 Preparation Score: {score['overall_score']}% - {score['status']}")
    print(f"   Attendees researched: {len(attendees)}/{len(meeting.get('attendees', []))}")
    print(f"   Documents gathered: {len(docs)}")
    print(f"   Emails analyzed: {len(emails)}")
    
    print("\n👥 ATTENDEE INTEL:")
    for att in attendees:
        print(f"\n   • {att['name']} ({att['role']})")
        print(f"     {att.get('notes', 'No notes')}")
    
    print("\n📄 RELEVANT DOCUMENTS:")
    for doc in docs:
        print(f"   • {doc['name']} (updated {doc['updated']})")
    
    print("\n📧 RECENT EMAILS:")
    for email in emails:
        print(f"   • {email['subject']} - from {email['from']}")


def cmd_attendees(args):
    """Get detailed attendee intel."""
    meetings = get_upcoming_meetings()
    meeting = next((m for m in meetings if m['id'] == args.meeting_id), None)
    
    if not meeting:
        print(f"❌ Meeting not found: {args.meeting_id}")
        return
    
    print(f"\n👥 ATTENDEES: {meeting['title']}")
    print("=" * 60)
    
    for email in meeting.get('attendees', []):
        intel = get_attendee_intel(email)
        if intel:
            print(f"\n🔹 {intel['name']}")
            print(f"   Role: {intel['role']}")
            print(f"   Department: {intel.get('department', 'Unknown')}")
            print(f"   Last interaction: {intel.get('last_interaction', 'Unknown')}")
            print(f"   Communication style: {intel.get('communication_style', 'Unknown')}")
            print(f"   Notes: {intel.get('notes', 'None')}")
        else:
            print(f"\n🔹 {email}")
            print(f"   ⚠️  No intel available")


def cmd_briefing(args):
    """Generate AI briefing."""
    meetings = get_upcoming_meetings()
    meeting = next((m for m in meetings if m['id'] == args.meeting_id), None)
    
    if not meeting:
        print(f"❌ Meeting not found: {args.meeting_id}")
        return
    
    attendees = [get_attendee_intel(email) for email in meeting.get('attendees', [])]
    attendees = [a for a in attendees if a]
    emails = get_related_emails(args.meeting_id)
    docs = get_related_documents(args.meeting_id)
    
    briefing = generate_briefing(meeting, attendees, emails, docs)
    print(briefing)


def cmd_export(args):
    """Export prep kit to JSON."""
    meetings = get_upcoming_meetings()
    meeting = next((m for m in meetings if m['id'] == args.meeting_id), None)
    
    if not meeting:
        print(f"❌ Meeting not found: {args.meeting_id}")
        return
    
    attendees = [get_attendee_intel(email) for email in meeting.get('attendees', [])]
    attendees = [a for a in attendees if a]
    emails = get_related_emails(args.meeting_id)
    docs = get_related_documents(args.meeting_id)
    score = calculate_prep_score(meeting, attendees, emails, docs)
    
    export_data = {
        "meeting": meeting,
        "attendees": attendees,
        "emails": emails,
        "documents": docs,
        "prep_score": score,
        "exported_at": datetime.now().isoformat()
    }
    
    output_file = args.output or f"prep-{args.meeting_id}.json"
    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2, default=str)
    
    print(f"✅ Prep kit exported to: {output_file}")


def cmd_search(args):
    """Search related docs and emails."""
    print(f"\n🔍 SEARCH RESULTS: '{args.query}'")
    print("=" * 60)
    
    # Search emails
    matching_emails = [e for e in SAMPLE_EMAILS if args.query.lower() in e['subject'].lower() or 
                       any(args.query.lower() in tag for tag in e.get('tags', []))]
    
    print(f"\n📧 EMAILS ({len(matching_emails)}):")
    for email in matching_emails:
        print(f"   • {email['subject']}")
        print(f"     From: {email['from']}")
    
    # Search docs
    matching_docs = [d for d in SAMPLE_DOCUMENTS if args.query.lower() in d['name'].lower()]
    
    print(f"\n📄 DOCUMENTS ({len(matching_docs)}):")
    for doc in matching_docs:
        print(f"   • {doc['name']} (updated {doc['updated']})")


def main():
    parser = argparse.ArgumentParser(description="Smart Meeting Prep - Gather intel before meetings")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # upcoming
    upcoming_parser = subparsers.add_parser('upcoming', help='List upcoming meetings')
    upcoming_parser.add_argument('-d', '--days', type=int, default=7, help='Days to look ahead')
    
    # prep
    prep_parser = subparsers.add_parser('prep', help='Generate meeting prep')
    prep_parser.add_argument('-m', '--meeting-id', required=True, help='Meeting ID')
    
    # attendees
    att_parser = subparsers.add_parser('attendees', help='Get attendee intel')
    att_parser.add_argument('-m', '--meeting-id', required=True, help='Meeting ID')
    
    # briefing
    brief_parser = subparsers.add_parser('briefing', help='Generate AI briefing')
    brief_parser.add_argument('-m', '--meeting-id', required=True, help='Meeting ID')
    
    # export
    export_parser = subparsers.add_parser('export', help='Export prep kit')
    export_parser.add_argument('-m', '--meeting-id', required=True, help='Meeting ID')
    export_parser.add_argument('-o', '--output', help='Output file path')
    
    # search
    search_parser = subparsers.add_parser('search', help='Search docs and emails')
    search_parser.add_argument('-q', '--query', required=True, help='Search query')
    
    args = parser.parse_args()
    
    if args.command == 'upcoming':
        cmd_upcoming(args)
    elif args.command == 'prep':
        cmd_prep(args)
    elif args.command == 'attendees':
        cmd_attendees(args)
    elif args.command == 'briefing':
        cmd_briefing(args)
    elif args.command == 'export':
        cmd_export(args)
    elif args.command == 'search':
        cmd_search(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
