#!/usr/bin/env python3
"""
Knowledge Base Builder
Auto-build a wiki from conversations, documents, and notes.

Usage:
    python kb_builder.py extract -f <file>         # Extract knowledge from file
    python kb_builder.py add -t "title" -c "..."   # Add article manually
    python kb_builder.py search -q "query"         # Search knowledge base
    python kb_builder.py list [--category CAT]     # List articles
    python kb_builder.py view -i <article_id>      # View article
    python kb_builder.py export [-o output/]       # Export as markdown wiki
    python kb_builder.py stats                     # Show KB statistics
    python kb_builder.py suggest                   # Suggest articles to create
    python kb_builder.py link                      # Auto-link related articles
"""

import argparse
import hashlib
import json
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

# Storage paths
DATA_DIR = Path(__file__).parent / "data"
ARTICLES_FILE = DATA_DIR / "articles.json"
INDEX_FILE = DATA_DIR / "index.json"
HISTORY_FILE = DATA_DIR / "history.json"


def ensure_data_dir():
    """Create data directory if needed."""
    DATA_DIR.mkdir(exist_ok=True)


def load_json(path: Path, default=None):
    """Load JSON file or return default."""
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default if default is not None else {}


def save_json(path: Path, data):
    """Save data to JSON file."""
    ensure_data_dir()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)


def generate_id(text: str) -> str:
    """Generate short ID from text."""
    return hashlib.md5(text.encode()).hexdigest()[:8]


def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text[:50]


# Knowledge extraction patterns
KNOWLEDGE_PATTERNS = {
    'definition': r'(?:is defined as|means|refers to|is)\s+["\']?([^.!?\n]+)',
    'how_to': r'(?:to\s+\w+,?\s+)?(?:you\s+)?(?:need to|should|must|can)\s+([^.!?\n]+)',
    'fact': r'(?:note that|remember|important[:]?|key point[:]?)\s+([^.!?\n]+)',
    'example': r'(?:for example|e\.g\.|such as|like)\s+([^.!?\n]+)',
    'comparison': r'(?:unlike|compared to|versus|vs\.?)\s+([^.!?\n]+)',
    'warning': r'(?:warning|caution|beware|don\'t|never)\s+([^.!?\n]+)',
    'tip': r'(?:tip|trick|hint|pro tip)\s*[:\-]?\s*([^.!?\n]+)',
}

# Categories for auto-classification
CATEGORY_KEYWORDS = {
    'technical': ['code', 'api', 'function', 'class', 'method', 'bug', 'error', 'deploy', 'server', 'database'],
    'process': ['workflow', 'process', 'procedure', 'step', 'guide', 'how to', 'tutorial'],
    'reference': ['definition', 'glossary', 'term', 'concept', 'meaning'],
    'troubleshooting': ['fix', 'issue', 'problem', 'error', 'debug', 'solve', 'resolution'],
    'best-practices': ['best practice', 'recommendation', 'should', 'avoid', 'pattern', 'tip'],
    'faq': ['question', 'answer', 'faq', 'common', 'frequently'],
    'meeting-notes': ['meeting', 'discussion', 'decision', 'action item', 'attendee'],
    'project': ['project', 'milestone', 'deadline', 'deliverable', 'requirement'],
}


def detect_category(text: str, title: str = '') -> str:
    """Auto-detect article category from content."""
    combined = (title + ' ' + text).lower()
    
    scores = defaultdict(int)
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in combined:
                scores[category] += 1
    
    if scores:
        return max(scores, key=scores.get)
    return 'general'


def extract_topics(text: str) -> List[str]:
    """Extract key topics from text."""
    # Common stop words
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
                  'may', 'might', 'must', 'shall', 'can', 'need', 'to', 'of', 'in', 'for',
                  'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during', 'before',
                  'after', 'above', 'below', 'between', 'under', 'again', 'further', 'then',
                  'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few',
                  'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
                  'same', 'so', 'than', 'too', 'very', 'just', 'and', 'but', 'if', 'or',
                  'because', 'until', 'while', 'this', 'that', 'these', 'those', 'it', 'its'}
    
    # Extract words
    words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_-]{2,}\b', text.lower())
    
    # Count frequencies
    freq = defaultdict(int)
    for word in words:
        if word not in stop_words:
            freq[word] += 1
    
    # Return top topics
    sorted_topics = sorted(freq.items(), key=lambda x: -x[1])
    return [topic for topic, count in sorted_topics[:10] if count >= 2]


def extract_knowledge_items(text: str) -> List[Dict]:
    """Extract knowledge items from text using patterns."""
    items = []
    
    for pattern_type, pattern in KNOWLEDGE_PATTERNS.items():
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            content = match.group(1).strip()
            if len(content) > 20:  # Filter short matches
                items.append({
                    'type': pattern_type,
                    'content': content,
                    'context': text[max(0, match.start()-50):match.end()+50]
                })
    
    return items


def extract_questions_answers(text: str) -> List[Dict]:
    """Extract Q&A pairs from text."""
    qa_pairs = []
    
    # Pattern: Q: ... A: ...
    qa_pattern = r'(?:Q|Question)[:\s]+([^\n?]+\??)\s*(?:A|Answer)[:\s]+([^\n]+)'
    for match in re.finditer(qa_pattern, text, re.IGNORECASE):
        qa_pairs.append({
            'question': match.group(1).strip(),
            'answer': match.group(2).strip()
        })
    
    # Pattern: "question?" followed by answer
    question_pattern = r'([A-Z][^.!?\n]*\?)\s+([A-Z][^.!?\n]+[.!])'
    for match in re.finditer(question_pattern, text):
        qa_pairs.append({
            'question': match.group(1).strip(),
            'answer': match.group(2).strip()
        })
    
    return qa_pairs


def create_article(title: str, content: str, category: str = None, 
                   tags: List[str] = None, source: str = None) -> Dict:
    """Create a new knowledge base article."""
    article_id = generate_id(title + str(datetime.now()))
    
    if not category:
        category = detect_category(content, title)
    
    if not tags:
        tags = extract_topics(content)[:5]
    
    # Extract structured knowledge
    knowledge_items = extract_knowledge_items(content)
    qa_pairs = extract_questions_answers(content)
    
    article = {
        'id': article_id,
        'title': title,
        'slug': slugify(title),
        'content': content,
        'category': category,
        'tags': tags,
        'source': source,
        'knowledge_items': knowledge_items,
        'qa_pairs': qa_pairs,
        'related_articles': [],
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'views': 0,
        'version': 1
    }
    
    return article


def add_article(article: Dict) -> str:
    """Add article to knowledge base."""
    articles = load_json(ARTICLES_FILE, {'articles': []})
    
    # Check for duplicate
    for existing in articles['articles']:
        if existing['title'].lower() == article['title'].lower():
            # Update existing
            existing.update(article)
            existing['updated_at'] = datetime.now().isoformat()
            existing['version'] += 1
            save_json(ARTICLES_FILE, articles)
            return existing['id']
    
    articles['articles'].append(article)
    save_json(ARTICLES_FILE, articles)
    
    # Update index
    update_index(article)
    
    return article['id']


def update_index(article: Dict):
    """Update search index with article."""
    index = load_json(INDEX_FILE, {'terms': {}, 'categories': {}, 'tags': {}})
    
    # Index by terms
    terms = set(extract_topics(article['title'] + ' ' + article['content']))
    for term in terms:
        if term not in index['terms']:
            index['terms'][term] = []
        if article['id'] not in index['terms'][term]:
            index['terms'][term].append(article['id'])
    
    # Index by category
    cat = article['category']
    if cat not in index['categories']:
        index['categories'][cat] = []
    if article['id'] not in index['categories'][cat]:
        index['categories'][cat].append(article['id'])
    
    # Index by tags
    for tag in article.get('tags', []):
        if tag not in index['tags']:
            index['tags'][tag] = []
        if article['id'] not in index['tags'][tag]:
            index['tags'][tag].append(article['id'])
    
    save_json(INDEX_FILE, index)


def search_articles(query: str, limit: int = 10) -> List[Dict]:
    """Search knowledge base."""
    articles = load_json(ARTICLES_FILE, {'articles': []})['articles']
    index = load_json(INDEX_FILE, {'terms': {}, 'categories': {}, 'tags': {}})
    
    query_terms = query.lower().split()
    scores = defaultdict(int)
    
    # Score by term matches
    for term in query_terms:
        for indexed_term, article_ids in index['terms'].items():
            if term in indexed_term or indexed_term in term:
                for aid in article_ids:
                    scores[aid] += 2 if term == indexed_term else 1
    
    # Score by tag matches
    for term in query_terms:
        for tag, article_ids in index['tags'].items():
            if term in tag:
                for aid in article_ids:
                    scores[aid] += 3
    
    # Score by content match
    for article in articles:
        content = (article['title'] + ' ' + article['content']).lower()
        for term in query_terms:
            if term in content:
                scores[article['id']] += content.count(term)
    
    # Sort by score
    sorted_ids = sorted(scores.keys(), key=lambda x: -scores[x])[:limit]
    
    results = []
    for aid in sorted_ids:
        for article in articles:
            if article['id'] == aid:
                results.append({**article, 'score': scores[aid]})
                break
    
    return results


def find_related_articles(article_id: str, limit: int = 5) -> List[Dict]:
    """Find articles related to given article."""
    articles = load_json(ARTICLES_FILE, {'articles': []})['articles']
    
    target = None
    for a in articles:
        if a['id'] == article_id:
            target = a
            break
    
    if not target:
        return []
    
    # Use tags and topics for similarity
    target_features = set(target.get('tags', []) + extract_topics(target['content']))
    
    similarities = []
    for article in articles:
        if article['id'] == article_id:
            continue
        
        article_features = set(article.get('tags', []) + extract_topics(article['content']))
        overlap = len(target_features & article_features)
        
        if overlap > 0:
            similarities.append((article, overlap))
    
    similarities.sort(key=lambda x: -x[1])
    return [s[0] for s in similarities[:limit]]


def auto_link_articles():
    """Automatically find and create links between related articles."""
    articles = load_json(ARTICLES_FILE, {'articles': []})
    
    for article in articles['articles']:
        related = find_related_articles(article['id'])
        article['related_articles'] = [r['id'] for r in related]
    
    save_json(ARTICLES_FILE, articles)
    return len(articles['articles'])


def export_wiki(output_dir: Path):
    """Export knowledge base as markdown wiki."""
    articles = load_json(ARTICLES_FILE, {'articles': []})['articles']
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create index page
    index_content = """# Knowledge Base

> Auto-generated wiki from conversations and documents

## Categories

"""
    
    # Group by category
    by_category = defaultdict(list)
    for article in articles:
        by_category[article['category']].append(article)
    
    for category in sorted(by_category.keys()):
        index_content += f"### {category.title().replace('-', ' ')}\n\n"
        for article in sorted(by_category[category], key=lambda x: x['title']):
            index_content += f"- [{article['title']}]({article['slug']}.md)\n"
        index_content += "\n"
    
    (output_dir / "index.md").write_text(index_content)
    
    # Create article pages
    for article in articles:
        content = f"""# {article['title']}

**Category:** {article['category']}  
**Tags:** {', '.join(article.get('tags', []))}  
**Last Updated:** {article['updated_at'][:10]}

---

{article['content']}

"""
        
        if article.get('qa_pairs'):
            content += "\n## FAQ\n\n"
            for qa in article['qa_pairs']:
                content += f"**Q: {qa['question']}**\n\n{qa['answer']}\n\n"
        
        if article.get('related_articles'):
            content += "\n## Related Articles\n\n"
            for related_id in article['related_articles']:
                for a in articles:
                    if a['id'] == related_id:
                        content += f"- [{a['title']}]({a['slug']}.md)\n"
                        break
        
        (output_dir / f"{article['slug']}.md").write_text(content)
    
    return len(articles)


def suggest_articles() -> List[Dict]:
    """Suggest articles that should be created based on gaps."""
    articles = load_json(ARTICLES_FILE, {'articles': []})['articles']
    index = load_json(INDEX_FILE, {'terms': {}, 'categories': {}, 'tags': {}})
    
    suggestions = []
    
    # Find frequently referenced but undefined terms
    term_counts = {term: len(ids) for term, ids in index['terms'].items()}
    
    # Find terms that appear often but don't have dedicated articles
    existing_slugs = {a['slug'] for a in articles}
    
    for term, count in sorted(term_counts.items(), key=lambda x: -x[1])[:20]:
        if slugify(term) not in existing_slugs and count >= 2:
            suggestions.append({
                'suggested_title': term.title(),
                'reason': f'Referenced in {count} articles',
                'type': 'definition'
            })
    
    # Find categories with few articles
    for category, article_ids in index['categories'].items():
        if len(article_ids) < 3:
            suggestions.append({
                'suggested_title': f'{category.title()} Overview',
                'reason': f'Category has only {len(article_ids)} articles',
                'type': 'overview'
            })
    
    return suggestions[:10]


def get_stats() -> Dict:
    """Get knowledge base statistics."""
    articles = load_json(ARTICLES_FILE, {'articles': []})['articles']
    index = load_json(INDEX_FILE, {'terms': {}, 'categories': {}, 'tags': {}})
    
    total_words = sum(len(a['content'].split()) for a in articles)
    
    return {
        'total_articles': len(articles),
        'total_words': total_words,
        'avg_words_per_article': total_words // max(len(articles), 1),
        'categories': {cat: len(ids) for cat, ids in index['categories'].items()},
        'top_tags': sorted(
            [(tag, len(ids)) for tag, ids in index['tags'].items()],
            key=lambda x: -x[1]
        )[:10],
        'total_qa_pairs': sum(len(a.get('qa_pairs', [])) for a in articles),
        'total_knowledge_items': sum(len(a.get('knowledge_items', [])) for a in articles)
    }


# CLI Commands
def cmd_extract(args):
    """Extract knowledge from a file."""
    filepath = Path(args.file)
    
    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        return
    
    content = filepath.read_text(encoding='utf-8')
    
    # Generate title from filename
    title = filepath.stem.replace('_', ' ').replace('-', ' ').title()
    
    print(f"📖 Extracting knowledge from: {filepath.name}")
    print(f"   Content length: {len(content)} chars")
    
    # Extract knowledge
    items = extract_knowledge_items(content)
    qa_pairs = extract_questions_answers(content)
    topics = extract_topics(content)
    category = detect_category(content, title)
    
    print(f"\n📊 EXTRACTION RESULTS:")
    print(f"   Category: {category}")
    print(f"   Topics: {', '.join(topics[:5])}")
    print(f"   Knowledge items: {len(items)}")
    print(f"   Q&A pairs: {len(qa_pairs)}")
    
    if items:
        print(f"\n💡 KNOWLEDGE ITEMS:")
        for item in items[:5]:
            print(f"   [{item['type']}] {item['content'][:80]}...")
    
    if qa_pairs:
        print(f"\n❓ Q&A PAIRS:")
        for qa in qa_pairs[:3]:
            print(f"   Q: {qa['question'][:60]}...")
            print(f"   A: {qa['answer'][:60]}...")
    
    if args.save:
        article = create_article(title, content, category, topics[:5], str(filepath))
        article_id = add_article(article)
        print(f"\n✅ Article created: {article_id}")


def cmd_add(args):
    """Add article manually."""
    article = create_article(
        title=args.title,
        content=args.content,
        category=args.category,
        tags=args.tags.split(',') if args.tags else None,
        source='manual'
    )
    
    article_id = add_article(article)
    print(f"✅ Article created: {article_id}")
    print(f"   Title: {args.title}")
    print(f"   Category: {article['category']}")
    print(f"   Tags: {', '.join(article['tags'])}")


def cmd_search(args):
    """Search knowledge base."""
    results = search_articles(args.query, args.limit)
    
    print(f"\n🔍 SEARCH RESULTS: '{args.query}'")
    print("=" * 50)
    
    if not results:
        print("   No results found")
        return
    
    for r in results:
        print(f"\n📄 {r['title']} (score: {r['score']})")
        print(f"   Category: {r['category']}")
        print(f"   Tags: {', '.join(r.get('tags', []))}")
        preview = r['content'][:150].replace('\n', ' ')
        print(f"   {preview}...")


def cmd_list(args):
    """List articles."""
    articles = load_json(ARTICLES_FILE, {'articles': []})['articles']
    
    if args.category:
        articles = [a for a in articles if a['category'] == args.category]
    
    print(f"\n📚 KNOWLEDGE BASE ({len(articles)} articles)")
    print("=" * 50)
    
    # Group by category
    by_cat = defaultdict(list)
    for a in articles:
        by_cat[a['category']].append(a)
    
    for cat in sorted(by_cat.keys()):
        print(f"\n📁 {cat.upper()}")
        for a in sorted(by_cat[cat], key=lambda x: x['title']):
            tags = ', '.join(a.get('tags', [])[:3])
            print(f"   • {a['title']} [{tags}]")


def cmd_view(args):
    """View article."""
    articles = load_json(ARTICLES_FILE, {'articles': []})['articles']
    
    article = None
    for a in articles:
        if a['id'] == args.id or a['slug'] == args.id:
            article = a
            break
    
    if not article:
        print(f"❌ Article not found: {args.id}")
        return
    
    print(f"\n{'=' * 60}")
    print(f"📄 {article['title']}")
    print(f"{'=' * 60}")
    print(f"Category: {article['category']}")
    print(f"Tags: {', '.join(article.get('tags', []))}")
    print(f"Created: {article['created_at'][:10]}")
    print(f"Updated: {article['updated_at'][:10]}")
    print(f"{'=' * 60}\n")
    print(article['content'])
    
    if article.get('qa_pairs'):
        print(f"\n{'=' * 60}")
        print("FAQ")
        print(f"{'=' * 60}")
        for qa in article['qa_pairs']:
            print(f"\nQ: {qa['question']}")
            print(f"A: {qa['answer']}")


def cmd_export(args):
    """Export as wiki."""
    output_dir = Path(args.output)
    count = export_wiki(output_dir)
    print(f"✅ Exported {count} articles to: {output_dir}")


def cmd_stats(args):
    """Show statistics."""
    stats = get_stats()
    
    print(f"\n📊 KNOWLEDGE BASE STATISTICS")
    print("=" * 50)
    print(f"📄 Total Articles: {stats['total_articles']}")
    print(f"📝 Total Words: {stats['total_words']:,}")
    print(f"📏 Avg Words/Article: {stats['avg_words_per_article']}")
    print(f"❓ Q&A Pairs: {stats['total_qa_pairs']}")
    print(f"💡 Knowledge Items: {stats['total_knowledge_items']}")
    
    print(f"\n📁 BY CATEGORY:")
    for cat, count in sorted(stats['categories'].items(), key=lambda x: -x[1]):
        bar = "█" * count + "░" * (10 - min(count, 10))
        print(f"   {cat:20} {bar} {count}")
    
    print(f"\n🏷️ TOP TAGS:")
    for tag, count in stats['top_tags']:
        print(f"   {tag}: {count}")


def cmd_suggest(args):
    """Suggest articles to create."""
    suggestions = suggest_articles()
    
    print(f"\n💡 SUGGESTED ARTICLES")
    print("=" * 50)
    
    if not suggestions:
        print("   No suggestions - knowledge base looks complete!")
        return
    
    for s in suggestions:
        print(f"\n📝 {s['suggested_title']}")
        print(f"   Type: {s['type']}")
        print(f"   Reason: {s['reason']}")


def cmd_link(args):
    """Auto-link related articles."""
    count = auto_link_articles()
    print(f"✅ Linked {count} articles")


def main():
    parser = argparse.ArgumentParser(description="Knowledge Base Builder")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # extract
    extract_parser = subparsers.add_parser('extract', help='Extract knowledge from file')
    extract_parser.add_argument('-f', '--file', required=True, help='File to extract from')
    extract_parser.add_argument('--save', action='store_true', help='Save as article')
    
    # add
    add_parser = subparsers.add_parser('add', help='Add article manually')
    add_parser.add_argument('-t', '--title', required=True, help='Article title')
    add_parser.add_argument('-c', '--content', required=True, help='Article content')
    add_parser.add_argument('--category', help='Category')
    add_parser.add_argument('--tags', help='Comma-separated tags')
    
    # search
    search_parser = subparsers.add_parser('search', help='Search knowledge base')
    search_parser.add_argument('-q', '--query', required=True, help='Search query')
    search_parser.add_argument('-l', '--limit', type=int, default=10, help='Max results')
    
    # list
    list_parser = subparsers.add_parser('list', help='List articles')
    list_parser.add_argument('--category', help='Filter by category')
    
    # view
    view_parser = subparsers.add_parser('view', help='View article')
    view_parser.add_argument('-i', '--id', required=True, help='Article ID or slug')
    
    # export
    export_parser = subparsers.add_parser('export', help='Export as wiki')
    export_parser.add_argument('-o', '--output', default='wiki', help='Output directory')
    
    # stats
    subparsers.add_parser('stats', help='Show statistics')
    
    # suggest
    subparsers.add_parser('suggest', help='Suggest articles')
    
    # link
    subparsers.add_parser('link', help='Auto-link articles')
    
    args = parser.parse_args()
    
    if args.command == 'extract':
        cmd_extract(args)
    elif args.command == 'add':
        cmd_add(args)
    elif args.command == 'search':
        cmd_search(args)
    elif args.command == 'list':
        cmd_list(args)
    elif args.command == 'view':
        cmd_view(args)
    elif args.command == 'export':
        cmd_export(args)
    elif args.command == 'stats':
        cmd_stats(args)
    elif args.command == 'suggest':
        cmd_suggest(args)
    elif args.command == 'link':
        cmd_link(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
