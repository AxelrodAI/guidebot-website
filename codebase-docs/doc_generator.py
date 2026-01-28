#!/usr/bin/env python3
"""
Codebase Documentation Generator
Auto-generate documentation from repository analysis.

Usage:
    python doc_generator.py analyze -d <directory>     # Analyze a codebase
    python doc_generator.py generate -d <dir> -o docs  # Generate markdown docs
    python doc_generator.py structure -d <directory>   # Show project structure
    python doc_generator.py stats -d <directory>       # Show codebase statistics
    python doc_generator.py functions -f <file>        # Extract functions from file
    python doc_generator.py readme -d <directory>      # Generate README.md
"""

import argparse
import ast
import json
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# File extensions to analyze
CODE_EXTENSIONS = {
    '.py': 'Python',
    '.js': 'JavaScript',
    '.ts': 'TypeScript',
    '.jsx': 'React JSX',
    '.tsx': 'React TSX',
    '.java': 'Java',
    '.cpp': 'C++',
    '.c': 'C',
    '.h': 'C Header',
    '.hpp': 'C++ Header',
    '.go': 'Go',
    '.rs': 'Rust',
    '.rb': 'Ruby',
    '.php': 'PHP',
    '.swift': 'Swift',
    '.kt': 'Kotlin',
    '.cs': 'C#',
    '.scala': 'Scala',
}

DOC_EXTENSIONS = {'.md', '.rst', '.txt', '.adoc'}
CONFIG_FILES = {'package.json', 'pyproject.toml', 'setup.py', 'Cargo.toml', 'go.mod', 'pom.xml'}

IGNORE_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'env', 
               'dist', 'build', '.next', '.cache', 'coverage', '.idea', '.vscode'}


def should_ignore(path: Path) -> bool:
    """Check if path should be ignored."""
    parts = set(path.parts)
    return bool(parts & IGNORE_DIRS)


def get_file_stats(filepath: Path) -> Dict:
    """Get statistics for a single file."""
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')
        
        # Count different line types
        code_lines = 0
        comment_lines = 0
        blank_lines = 0
        
        in_multiline_comment = False
        ext = filepath.suffix.lower()
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                blank_lines += 1
            elif ext == '.py':
                if stripped.startswith('#'):
                    comment_lines += 1
                elif '"""' in stripped or "'''" in stripped:
                    comment_lines += 1
                    if stripped.count('"""') == 1 or stripped.count("'''") == 1:
                        in_multiline_comment = not in_multiline_comment
                elif in_multiline_comment:
                    comment_lines += 1
                else:
                    code_lines += 1
            elif ext in {'.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.go', '.rs'}:
                if stripped.startswith('//'):
                    comment_lines += 1
                elif stripped.startswith('/*'):
                    comment_lines += 1
                    if '*/' not in stripped:
                        in_multiline_comment = True
                elif in_multiline_comment:
                    comment_lines += 1
                    if '*/' in stripped:
                        in_multiline_comment = False
                else:
                    code_lines += 1
            else:
                code_lines += 1
        
        return {
            'total_lines': len(lines),
            'code_lines': code_lines,
            'comment_lines': comment_lines,
            'blank_lines': blank_lines,
            'size_bytes': filepath.stat().st_size
        }
    except Exception as e:
        return {'error': str(e)}


def extract_python_info(filepath: Path) -> Dict:
    """Extract detailed info from Python file using AST."""
    try:
        content = filepath.read_text(encoding='utf-8')
        tree = ast.parse(content)
        
        info = {
            'module_docstring': ast.get_docstring(tree),
            'imports': [],
            'classes': [],
            'functions': [],
            'constants': []
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    info['imports'].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    info['imports'].append(f"{module}.{alias.name}")
            elif isinstance(node, ast.ClassDef):
                class_info = {
                    'name': node.name,
                    'docstring': ast.get_docstring(node),
                    'methods': [],
                    'bases': [base.id if isinstance(base, ast.Name) else str(base) for base in node.bases],
                    'decorators': [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list]
                }
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_info = {
                            'name': item.name,
                            'docstring': ast.get_docstring(item),
                            'args': [arg.arg for arg in item.args.args],
                            'decorators': [d.id if isinstance(d, ast.Name) else str(d) for d in item.decorator_list]
                        }
                        class_info['methods'].append(method_info)
                info['classes'].append(class_info)
            elif isinstance(node, ast.FunctionDef) and not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree)):
                # Top-level function
                func_info = {
                    'name': node.name,
                    'docstring': ast.get_docstring(node),
                    'args': [arg.arg for arg in node.args.args],
                    'decorators': [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list],
                    'returns': ast.unparse(node.returns) if node.returns else None
                }
                info['functions'].append(func_info)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        info['constants'].append(target.id)
        
        return info
    except Exception as e:
        return {'error': str(e)}


def extract_js_info(filepath: Path) -> Dict:
    """Extract info from JavaScript/TypeScript file using regex."""
    try:
        content = filepath.read_text(encoding='utf-8')
        
        info = {
            'imports': [],
            'exports': [],
            'functions': [],
            'classes': [],
            'react_components': []
        }
        
        # Extract imports
        import_pattern = r"import\s+(?:{[^}]+}|\*\s+as\s+\w+|\w+)\s+from\s+['\"]([^'\"]+)['\"]"
        info['imports'] = re.findall(import_pattern, content)
        
        # Extract exports
        export_pattern = r"export\s+(?:default\s+)?(?:const|let|var|function|class)\s+(\w+)"
        info['exports'] = re.findall(export_pattern, content)
        
        # Extract functions
        func_pattern = r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\([^)]*\)"
        info['functions'] = re.findall(func_pattern, content)
        
        # Extract arrow functions
        arrow_pattern = r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>"
        info['functions'].extend(re.findall(arrow_pattern, content))
        
        # Extract classes
        class_pattern = r"(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?"
        for match in re.finditer(class_pattern, content):
            info['classes'].append({
                'name': match.group(1),
                'extends': match.group(2)
            })
        
        # Detect React components (capitalized function returning JSX)
        component_pattern = r"(?:export\s+)?(?:const|function)\s+([A-Z]\w+)"
        potential_components = re.findall(component_pattern, content)
        if '<' in content and any(f"<{comp}" in content or "return (" in content for comp in potential_components):
            info['react_components'] = potential_components
        
        return info
    except Exception as e:
        return {'error': str(e)}


def analyze_directory(directory: Path) -> Dict:
    """Analyze an entire directory/codebase."""
    results = {
        'root': str(directory),
        'analyzed_at': datetime.now().isoformat(),
        'summary': {
            'total_files': 0,
            'total_lines': 0,
            'total_code_lines': 0,
            'total_size_bytes': 0,
            'languages': defaultdict(lambda: {'files': 0, 'lines': 0})
        },
        'files': [],
        'structure': {},
        'dependencies': set()
    }
    
    for filepath in directory.rglob('*'):
        if filepath.is_file() and not should_ignore(filepath):
            ext = filepath.suffix.lower()
            
            if ext in CODE_EXTENSIONS:
                stats = get_file_stats(filepath)
                rel_path = str(filepath.relative_to(directory))
                
                file_info = {
                    'path': rel_path,
                    'language': CODE_EXTENSIONS[ext],
                    'stats': stats
                }
                
                # Extract detailed info for supported languages
                if ext == '.py':
                    file_info['details'] = extract_python_info(filepath)
                elif ext in {'.js', '.ts', '.jsx', '.tsx'}:
                    file_info['details'] = extract_js_info(filepath)
                
                results['files'].append(file_info)
                results['summary']['total_files'] += 1
                
                if 'error' not in stats:
                    results['summary']['total_lines'] += stats['total_lines']
                    results['summary']['total_code_lines'] += stats['code_lines']
                    results['summary']['total_size_bytes'] += stats['size_bytes']
                    
                    lang = CODE_EXTENSIONS[ext]
                    results['summary']['languages'][lang]['files'] += 1
                    results['summary']['languages'][lang]['lines'] += stats['total_lines']
            
            # Check for config/dependency files
            if filepath.name in CONFIG_FILES:
                results['dependencies'].add(filepath.name)
    
    results['dependencies'] = list(results['dependencies'])
    results['summary']['languages'] = dict(results['summary']['languages'])
    
    return results


def generate_project_structure(directory: Path, prefix: str = "", max_depth: int = 4) -> str:
    """Generate a tree view of project structure."""
    output = []
    
    def add_tree(path: Path, prefix: str, depth: int):
        if depth > max_depth:
            return
        
        items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        dirs = [i for i in items if i.is_dir() and i.name not in IGNORE_DIRS]
        files = [i for i in items if i.is_file()]
        
        # Limit files shown per directory
        shown_files = files[:10]
        hidden_files = len(files) - len(shown_files)
        
        for i, item in enumerate(dirs + shown_files):
            is_last = (i == len(dirs) + len(shown_files) - 1) and hidden_files == 0
            connector = "└── " if is_last else "├── "
            
            if item.is_dir():
                output.append(f"{prefix}{connector}📁 {item.name}/")
                new_prefix = prefix + ("    " if is_last else "│   ")
                add_tree(item, new_prefix, depth + 1)
            else:
                ext = item.suffix.lower()
                icon = "🐍" if ext == '.py' else "📜" if ext in {'.js', '.ts'} else "📄"
                output.append(f"{prefix}{connector}{icon} {item.name}")
        
        if hidden_files > 0:
            output.append(f"{prefix}└── ... and {hidden_files} more files")
    
    output.append(f"📁 {directory.name}/")
    add_tree(directory, "", 0)
    
    return "\n".join(output)


def generate_readme(analysis: Dict) -> str:
    """Generate a README.md from analysis."""
    summary = analysis['summary']
    
    readme = f"""# Project Documentation

> Auto-generated documentation for `{Path(analysis['root']).name}`

## Overview

| Metric | Value |
|--------|-------|
| Total Files | {summary['total_files']} |
| Total Lines | {summary['total_lines']:,} |
| Code Lines | {summary['total_code_lines']:,} |
| Size | {summary['total_size_bytes'] / 1024:.1f} KB |

## Languages

| Language | Files | Lines |
|----------|-------|-------|
"""
    
    for lang, stats in sorted(summary['languages'].items(), key=lambda x: -x[1]['lines']):
        readme += f"| {lang} | {stats['files']} | {stats['lines']:,} |\n"
    
    readme += """
## Project Structure

```
"""
    readme += generate_project_structure(Path(analysis['root']))
    readme += """
```

## Key Files

"""
    
    # Find and document key files
    for file_info in sorted(analysis['files'], key=lambda x: -x['stats'].get('code_lines', 0))[:10]:
        readme += f"### `{file_info['path']}`\n\n"
        readme += f"- **Language:** {file_info['language']}\n"
        readme += f"- **Lines:** {file_info['stats'].get('total_lines', 'N/A')}\n"
        
        if 'details' in file_info and file_info['details']:
            details = file_info['details']
            if 'error' not in details:
                if details.get('module_docstring'):
                    readme += f"- **Description:** {details['module_docstring'][:200]}...\n" if len(details.get('module_docstring', '')) > 200 else f"- **Description:** {details.get('module_docstring')}\n"
                
                if details.get('classes'):
                    readme += f"- **Classes:** {', '.join(c['name'] for c in details['classes'])}\n"
                
                if details.get('functions'):
                    funcs = details['functions'][:5]
                    readme += f"- **Functions:** {', '.join(f['name'] if isinstance(f, dict) else f for f in funcs)}"
                    if len(details['functions']) > 5:
                        readme += f" (+{len(details['functions']) - 5} more)"
                    readme += "\n"
        
        readme += "\n"
    
    # Dependencies
    if analysis.get('dependencies'):
        readme += "## Dependencies\n\n"
        readme += "Found configuration files:\n"
        for dep in analysis['dependencies']:
            readme += f"- `{dep}`\n"
        readme += "\n"
    
    readme += f"""
---

*Generated by Codebase Documentation Generator on {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""
    
    return readme


def generate_api_docs(analysis: Dict) -> str:
    """Generate API documentation from analysis."""
    docs = """# API Reference

> Auto-generated API documentation

"""
    
    for file_info in analysis['files']:
        if 'details' not in file_info or 'error' in file_info.get('details', {}):
            continue
        
        details = file_info['details']
        has_content = details.get('classes') or details.get('functions')
        
        if not has_content:
            continue
        
        docs += f"## `{file_info['path']}`\n\n"
        
        if details.get('module_docstring'):
            docs += f"{details['module_docstring']}\n\n"
        
        # Document classes
        for cls in details.get('classes', []):
            docs += f"### class `{cls['name']}`\n\n"
            
            if cls.get('bases'):
                docs += f"**Inherits from:** {', '.join(cls['bases'])}\n\n"
            
            if cls.get('docstring'):
                docs += f"{cls['docstring']}\n\n"
            
            if cls.get('methods'):
                docs += "**Methods:**\n\n"
                for method in cls['methods']:
                    args = ', '.join(method.get('args', []))
                    docs += f"- `{method['name']}({args})`"
                    if method.get('docstring'):
                        first_line = method['docstring'].split('\n')[0]
                        docs += f" - {first_line}"
                    docs += "\n"
                docs += "\n"
        
        # Document functions
        for func in details.get('functions', []):
            if isinstance(func, dict):
                args = ', '.join(func.get('args', []))
                returns = f" -> {func['returns']}" if func.get('returns') else ""
                docs += f"### `{func['name']}({args}){returns}`\n\n"
                
                if func.get('docstring'):
                    docs += f"{func['docstring']}\n\n"
            else:
                docs += f"### `{func}()`\n\n"
        
        docs += "---\n\n"
    
    return docs


def cmd_analyze(args):
    """Analyze a codebase."""
    directory = Path(args.directory).resolve()
    
    if not directory.exists():
        print(f"❌ Directory not found: {directory}")
        return
    
    print(f"🔍 Analyzing {directory}...")
    analysis = analyze_directory(directory)
    
    summary = analysis['summary']
    print(f"\n📊 CODEBASE ANALYSIS")
    print("=" * 50)
    print(f"📁 Root: {analysis['root']}")
    print(f"📄 Total Files: {summary['total_files']}")
    print(f"📝 Total Lines: {summary['total_lines']:,}")
    print(f"💻 Code Lines: {summary['total_code_lines']:,}")
    print(f"📦 Size: {summary['total_size_bytes'] / 1024:.1f} KB")
    
    print(f"\n🗣️ LANGUAGES:")
    for lang, stats in sorted(summary['languages'].items(), key=lambda x: -x[1]['lines']):
        print(f"   {lang}: {stats['files']} files, {stats['lines']:,} lines")
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        print(f"\n✅ Analysis saved to: {args.output}")


def cmd_generate(args):
    """Generate documentation."""
    directory = Path(args.directory).resolve()
    output_dir = Path(args.output)
    
    print(f"🔍 Analyzing {directory}...")
    analysis = analyze_directory(directory)
    
    output_dir.mkdir(exist_ok=True)
    
    # Generate README
    readme = generate_readme(analysis)
    readme_path = output_dir / "README.md"
    readme_path.write_text(readme)
    print(f"✅ Generated: {readme_path}")
    
    # Generate API docs
    api_docs = generate_api_docs(analysis)
    api_path = output_dir / "API.md"
    api_path.write_text(api_docs)
    print(f"✅ Generated: {api_path}")
    
    # Save raw analysis
    analysis_path = output_dir / "analysis.json"
    with open(analysis_path, 'w') as f:
        json.dump(analysis, f, indent=2, default=str)
    print(f"✅ Generated: {analysis_path}")
    
    print(f"\n📚 Documentation generated in: {output_dir}")


def cmd_structure(args):
    """Show project structure."""
    directory = Path(args.directory).resolve()
    
    if not directory.exists():
        print(f"❌ Directory not found: {directory}")
        return
    
    print(f"\n📂 PROJECT STRUCTURE")
    print("=" * 50)
    print(generate_project_structure(directory, max_depth=args.depth))


def cmd_stats(args):
    """Show codebase statistics."""
    directory = Path(args.directory).resolve()
    
    print(f"🔍 Calculating statistics for {directory}...")
    analysis = analyze_directory(directory)
    
    summary = analysis['summary']
    
    print(f"\n📊 CODEBASE STATISTICS")
    print("=" * 50)
    
    # Overall stats
    print(f"\n📈 OVERALL:")
    print(f"   Files: {summary['total_files']}")
    print(f"   Lines: {summary['total_lines']:,}")
    print(f"   Code Lines: {summary['total_code_lines']:,}")
    print(f"   Comment Ratio: {(summary['total_lines'] - summary['total_code_lines']) / max(summary['total_lines'], 1) * 100:.1f}%")
    print(f"   Avg Lines/File: {summary['total_lines'] / max(summary['total_files'], 1):.0f}")
    
    # By language
    print(f"\n🗣️ BY LANGUAGE:")
    for lang, stats in sorted(summary['languages'].items(), key=lambda x: -x[1]['lines']):
        pct = stats['lines'] / max(summary['total_lines'], 1) * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"   {lang:15} {bar} {pct:5.1f}% ({stats['files']} files)")
    
    # Largest files
    print(f"\n📄 LARGEST FILES:")
    sorted_files = sorted(analysis['files'], key=lambda x: -x['stats'].get('code_lines', 0))[:10]
    for f in sorted_files:
        print(f"   {f['path']:40} {f['stats'].get('code_lines', 0):>6} lines")


def cmd_functions(args):
    """Extract functions from a file."""
    filepath = Path(args.file).resolve()
    
    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        return
    
    ext = filepath.suffix.lower()
    
    if ext == '.py':
        info = extract_python_info(filepath)
    elif ext in {'.js', '.ts', '.jsx', '.tsx'}:
        info = extract_js_info(filepath)
    else:
        print(f"❌ Unsupported file type: {ext}")
        return
    
    if 'error' in info:
        print(f"❌ Error: {info['error']}")
        return
    
    print(f"\n📄 {filepath.name}")
    print("=" * 50)
    
    if info.get('classes'):
        print(f"\n🏛️ CLASSES ({len(info['classes'])}):")
        for cls in info['classes']:
            if isinstance(cls, dict):
                print(f"\n   class {cls['name']}")
                if cls.get('docstring'):
                    print(f"      \"{cls['docstring'][:80]}...\"" if len(cls.get('docstring', '')) > 80 else f"      \"{cls.get('docstring')}\"")
                if cls.get('methods'):
                    for method in cls['methods']:
                        print(f"      - {method['name']}()")
            else:
                print(f"   class {cls}")
    
    if info.get('functions'):
        print(f"\n⚡ FUNCTIONS ({len(info['functions'])}):")
        for func in info['functions']:
            if isinstance(func, dict):
                args = ', '.join(func.get('args', []))
                print(f"   def {func['name']}({args})")
                if func.get('docstring'):
                    print(f"      \"{func['docstring'][:80]}...\"" if len(func.get('docstring', '')) > 80 else f"      \"{func.get('docstring')}\"")
            else:
                print(f"   function {func}()")


def cmd_readme(args):
    """Generate README.md for a project."""
    directory = Path(args.directory).resolve()
    
    print(f"🔍 Analyzing {directory}...")
    analysis = analyze_directory(directory)
    
    readme = generate_readme(analysis)
    
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = directory / "README.generated.md"
    
    output_path.write_text(readme)
    print(f"✅ README generated: {output_path}")
    
    if args.preview:
        print("\n" + "=" * 50)
        print(readme[:2000])
        if len(readme) > 2000:
            print(f"\n... ({len(readme) - 2000} more characters)")


def main():
    parser = argparse.ArgumentParser(description="Codebase Documentation Generator")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # analyze
    analyze_parser = subparsers.add_parser('analyze', help='Analyze a codebase')
    analyze_parser.add_argument('-d', '--directory', required=True, help='Directory to analyze')
    analyze_parser.add_argument('-o', '--output', help='Output JSON file')
    
    # generate
    gen_parser = subparsers.add_parser('generate', help='Generate documentation')
    gen_parser.add_argument('-d', '--directory', required=True, help='Directory to analyze')
    gen_parser.add_argument('-o', '--output', default='docs', help='Output directory')
    
    # structure
    struct_parser = subparsers.add_parser('structure', help='Show project structure')
    struct_parser.add_argument('-d', '--directory', required=True, help='Directory')
    struct_parser.add_argument('--depth', type=int, default=4, help='Max depth')
    
    # stats
    stats_parser = subparsers.add_parser('stats', help='Show codebase statistics')
    stats_parser.add_argument('-d', '--directory', required=True, help='Directory')
    
    # functions
    func_parser = subparsers.add_parser('functions', help='Extract functions from file')
    func_parser.add_argument('-f', '--file', required=True, help='File to analyze')
    
    # readme
    readme_parser = subparsers.add_parser('readme', help='Generate README')
    readme_parser.add_argument('-d', '--directory', required=True, help='Directory')
    readme_parser.add_argument('-o', '--output', help='Output file')
    readme_parser.add_argument('--preview', action='store_true', help='Preview output')
    
    args = parser.parse_args()
    
    if args.command == 'analyze':
        cmd_analyze(args)
    elif args.command == 'generate':
        cmd_generate(args)
    elif args.command == 'structure':
        cmd_structure(args)
    elif args.command == 'stats':
        cmd_stats(args)
    elif args.command == 'functions':
        cmd_functions(args)
    elif args.command == 'readme':
        cmd_readme(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
