#!/usr/bin/env python3
"""
Code Review Assistant Engine
=============================
Auto-review code for issues, security concerns, and style problems.
Supports Python, JavaScript, and generic pattern matching.

Usage:
    python review_engine.py review -f script.py
    python review_engine.py review -d ./src
    python review_engine.py rules
    python review_engine.py stats
"""

import argparse
import ast
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict
from typing import List, Dict, Any

# Data directory
DATA_DIR = Path(__file__).parent / "data"
HISTORY_FILE = DATA_DIR / "review_history.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

# Severity levels
SEVERITY = {
    "critical": {"emoji": "🔴", "weight": 10},
    "high": {"emoji": "🟠", "weight": 5},
    "medium": {"emoji": "🟡", "weight": 3},
    "low": {"emoji": "🟢", "weight": 1},
    "info": {"emoji": "ℹ️", "weight": 0}
}

# Rule categories
CATEGORIES = {
    "security": "🔒 Security",
    "performance": "⚡ Performance",
    "style": "🎨 Style",
    "bug": "🐛 Potential Bug",
    "complexity": "🔄 Complexity",
    "maintainability": "📚 Maintainability",
    "best_practice": "✅ Best Practice"
}

# Python-specific patterns
PYTHON_PATTERNS = [
    # Security
    {
        "id": "PY001",
        "pattern": r"\beval\s*\(",
        "message": "Use of eval() is dangerous - can execute arbitrary code",
        "severity": "critical",
        "category": "security",
        "suggestion": "Use ast.literal_eval() for safe evaluation of literals"
    },
    {
        "id": "PY002",
        "pattern": r"\bexec\s*\(",
        "message": "Use of exec() can execute arbitrary code",
        "severity": "critical",
        "category": "security",
        "suggestion": "Avoid exec() or carefully validate input"
    },
    {
        "id": "PY003",
        "pattern": r"pickle\.(load|loads)\s*\(",
        "message": "Pickle deserialization can execute arbitrary code",
        "severity": "high",
        "category": "security",
        "suggestion": "Use JSON or implement custom deserializer"
    },
    {
        "id": "PY004",
        "pattern": r"os\.system\s*\(",
        "message": "os.system() is vulnerable to shell injection",
        "severity": "high",
        "category": "security",
        "suggestion": "Use subprocess.run() with shell=False"
    },
    {
        "id": "PY005",
        "pattern": r"subprocess\.[^(]+\([^)]*shell\s*=\s*True",
        "message": "subprocess with shell=True is vulnerable to injection",
        "severity": "high",
        "category": "security",
        "suggestion": "Use shell=False and pass args as list"
    },
    {
        "id": "PY006",
        "pattern": r"(password|secret|api_key|apikey|token)\s*=\s*['\"][^'\"]+['\"]",
        "message": "Hardcoded credential detected",
        "severity": "critical",
        "category": "security",
        "suggestion": "Use environment variables or secrets manager"
    },
    # Performance
    {
        "id": "PY010",
        "pattern": r"for\s+\w+\s+in\s+range\s*\(\s*len\s*\(",
        "message": "Use enumerate() instead of range(len())",
        "severity": "low",
        "category": "performance",
        "suggestion": "for i, item in enumerate(items):"
    },
    {
        "id": "PY011",
        "pattern": r"\+\s*=\s*['\"].*?['\"]\s*$",
        "message": "String concatenation in loop may be slow",
        "severity": "low",
        "category": "performance",
        "suggestion": "Use ''.join() or f-strings"
    },
    {
        "id": "PY012",
        "pattern": r"\.append\s*\([^)]+\)\s*$",
        "message": "Consider list comprehension if in a loop",
        "severity": "info",
        "category": "performance",
        "suggestion": "List comprehensions are often faster"
    },
    # Bug potential
    {
        "id": "PY020",
        "pattern": r"except\s*:",
        "message": "Bare except catches all exceptions including KeyboardInterrupt",
        "severity": "medium",
        "category": "bug",
        "suggestion": "Use 'except Exception:' or specific exceptions"
    },
    {
        "id": "PY021",
        "pattern": r"except\s+\w+\s*,\s*\w+\s*:",
        "message": "Old-style exception syntax (Python 2)",
        "severity": "medium",
        "category": "bug",
        "suggestion": "Use 'except Exception as e:'"
    },
    {
        "id": "PY022",
        "pattern": r"def\s+\w+\s*\([^)]*=\s*\[\s*\]",
        "message": "Mutable default argument (list)",
        "severity": "high",
        "category": "bug",
        "suggestion": "Use None as default, initialize in function body"
    },
    {
        "id": "PY023",
        "pattern": r"def\s+\w+\s*\([^)]*=\s*\{\s*\}",
        "message": "Mutable default argument (dict)",
        "severity": "high",
        "category": "bug",
        "suggestion": "Use None as default, initialize in function body"
    },
    {
        "id": "PY024",
        "pattern": r"==\s*None|None\s*==",
        "message": "Use 'is None' instead of '== None'",
        "severity": "low",
        "category": "style",
        "suggestion": "if x is None:"
    },
    {
        "id": "PY025",
        "pattern": r"!=\s*None|None\s*!=",
        "message": "Use 'is not None' instead of '!= None'",
        "severity": "low",
        "category": "style",
        "suggestion": "if x is not None:"
    },
    # Style
    {
        "id": "PY030",
        "pattern": r"#\s*TODO\b",
        "message": "TODO comment found",
        "severity": "info",
        "category": "maintainability",
        "suggestion": "Track TODOs and resolve before release"
    },
    {
        "id": "PY031",
        "pattern": r"#\s*FIXME\b",
        "message": "FIXME comment found",
        "severity": "medium",
        "category": "bug",
        "suggestion": "Address FIXME before release"
    },
    {
        "id": "PY032",
        "pattern": r"#\s*HACK\b",
        "message": "HACK comment found - technical debt",
        "severity": "medium",
        "category": "maintainability",
        "suggestion": "Refactor hack when possible"
    },
    {
        "id": "PY033",
        "pattern": r"print\s*\(",
        "message": "Print statement found - use logging in production",
        "severity": "info",
        "category": "best_practice",
        "suggestion": "Use logging module for production code"
    },
    # Complexity
    {
        "id": "PY040",
        "pattern": r"if.*?if.*?if.*?:",
        "message": "Deeply nested conditionals",
        "severity": "medium",
        "category": "complexity",
        "suggestion": "Consider early returns or extracting to functions"
    },
]

# JavaScript-specific patterns
JS_PATTERNS = [
    # Security
    {
        "id": "JS001",
        "pattern": r"\beval\s*\(",
        "message": "eval() is dangerous - can execute arbitrary code",
        "severity": "critical",
        "category": "security",
        "suggestion": "Use JSON.parse() for data, avoid eval entirely"
    },
    {
        "id": "JS002",
        "pattern": r"innerHTML\s*=",
        "message": "innerHTML assignment can lead to XSS",
        "severity": "high",
        "category": "security",
        "suggestion": "Use textContent or sanitize HTML"
    },
    {
        "id": "JS003",
        "pattern": r"document\.write\s*\(",
        "message": "document.write() is a security risk",
        "severity": "high",
        "category": "security",
        "suggestion": "Use DOM manipulation methods instead"
    },
    {
        "id": "JS004",
        "pattern": r"localStorage\.(set|get)Item.*?(password|token|secret)",
        "message": "Sensitive data in localStorage",
        "severity": "high",
        "category": "security",
        "suggestion": "Use secure, httpOnly cookies for sensitive data"
    },
    # Best practices
    {
        "id": "JS010",
        "pattern": r"\bvar\s+",
        "message": "var is function-scoped - use let/const",
        "severity": "low",
        "category": "best_practice",
        "suggestion": "Use const for constants, let for variables"
    },
    {
        "id": "JS011",
        "pattern": r"==(?!=)",
        "message": "Use === for strict equality",
        "severity": "medium",
        "category": "bug",
        "suggestion": "=== prevents type coercion bugs"
    },
    {
        "id": "JS012",
        "pattern": r"!=(?!=)",
        "message": "Use !== for strict inequality",
        "severity": "medium",
        "category": "bug",
        "suggestion": "!== prevents type coercion bugs"
    },
    {
        "id": "JS013",
        "pattern": r"console\.(log|warn|error|debug)\s*\(",
        "message": "Console statement found",
        "severity": "info",
        "category": "best_practice",
        "suggestion": "Remove console statements for production"
    },
    {
        "id": "JS014",
        "pattern": r"debugger\s*;",
        "message": "Debugger statement found",
        "severity": "medium",
        "category": "bug",
        "suggestion": "Remove debugger statements"
    },
]

# Generic patterns (all languages)
GENERIC_PATTERNS = [
    {
        "id": "GEN001",
        "pattern": r"(?i)(password|passwd|pwd)\s*=\s*['\"][^'\"]{3,}['\"]",
        "message": "Possible hardcoded password",
        "severity": "critical",
        "category": "security",
        "suggestion": "Use environment variables or secrets manager"
    },
    {
        "id": "GEN002",
        "pattern": r"(?i)(api[_-]?key|apikey)\s*=\s*['\"][^'\"]{10,}['\"]",
        "message": "Possible hardcoded API key",
        "severity": "critical",
        "category": "security",
        "suggestion": "Use environment variables"
    },
    {
        "id": "GEN003",
        "pattern": r"(?i)(secret|token)\s*=\s*['\"][^'\"]{10,}['\"]",
        "message": "Possible hardcoded secret/token",
        "severity": "critical",
        "category": "security",
        "suggestion": "Use environment variables or secrets manager"
    },
    {
        "id": "GEN004",
        "pattern": r"(?i)#\s*XXX\b",
        "message": "XXX comment found - needs attention",
        "severity": "medium",
        "category": "maintainability",
        "suggestion": "Address XXX comments"
    },
    {
        "id": "GEN005",
        "pattern": r"https?://localhost",
        "message": "Localhost URL in code",
        "severity": "low",
        "category": "best_practice",
        "suggestion": "Use configuration for URLs"
    },
]


class CodeReviewEngine:
    """Code review assistant engine."""
    
    def __init__(self):
        self._ensure_data_dir()
        self.history = self._load_history()
        self.settings = self._load_settings()
        
    def _ensure_data_dir(self):
        """Create data directory if needed."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
    def _load_history(self) -> list:
        """Load review history."""
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_history(self):
        """Save review history."""
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.history[-100:], f, indent=2)  # Keep last 100
            
    def _load_settings(self) -> dict:
        """Load settings."""
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "min_severity": "info",
            "enabled_categories": list(CATEGORIES.keys()),
            "ignore_patterns": []
        }
    
    def _save_settings(self):
        """Save settings."""
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=2)
    
    def _detect_language(self, filepath: str) -> str:
        """Detect language from file extension."""
        ext = Path(filepath).suffix.lower()
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.cs': 'csharp',
        }
        return lang_map.get(ext, 'generic')
    
    def _get_patterns_for_language(self, language: str) -> list:
        """Get relevant patterns for a language."""
        patterns = GENERIC_PATTERNS.copy()
        
        if language == 'python':
            patterns.extend(PYTHON_PATTERNS)
        elif language in ('javascript', 'typescript'):
            patterns.extend(JS_PATTERNS)
            
        return patterns
    
    def _analyze_python_ast(self, content: str, filepath: str) -> List[Dict]:
        """Analyze Python code using AST for deeper issues."""
        issues = []
        
        try:
            tree = ast.parse(content)
            
            # Check for function complexity
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Count branches for cyclomatic complexity approximation
                    branches = 0
                    for child in ast.walk(node):
                        if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                            branches += 1
                    
                    if branches > 10:
                        issues.append({
                            "rule_id": "AST001",
                            "message": f"Function '{node.name}' has high complexity ({branches} branches)",
                            "severity": "medium",
                            "category": "complexity",
                            "line": node.lineno,
                            "suggestion": "Consider breaking into smaller functions"
                        })
                    
                    # Check function length
                    if hasattr(node, 'end_lineno') and node.end_lineno:
                        length = node.end_lineno - node.lineno
                        if length > 50:
                            issues.append({
                                "rule_id": "AST002",
                                "message": f"Function '{node.name}' is too long ({length} lines)",
                                "severity": "low",
                                "category": "maintainability",
                                "line": node.lineno,
                                "suggestion": "Keep functions under 50 lines"
                            })
                            
                # Check for too many arguments
                if isinstance(node, ast.arguments):
                    arg_count = len(node.args) + len(node.kwonlyargs)
                    if arg_count > 5:
                        issues.append({
                            "rule_id": "AST003",
                            "message": f"Too many function arguments ({arg_count})",
                            "severity": "low",
                            "category": "complexity",
                            "line": getattr(node, 'lineno', 0),
                            "suggestion": "Consider using a config object or dataclass"
                        })
                        
        except SyntaxError as e:
            issues.append({
                "rule_id": "AST000",
                "message": f"Syntax error: {e.msg}",
                "severity": "critical",
                "category": "bug",
                "line": e.lineno or 0,
                "suggestion": "Fix syntax error"
            })
            
        return issues
    
    def review_file(self, filepath: str) -> Dict[str, Any]:
        """Review a single file."""
        path = Path(filepath)
        
        if not path.exists():
            return {"error": f"File not found: {filepath}"}
        
        if not path.is_file():
            return {"error": f"Not a file: {filepath}"}
        
        try:
            content = path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            return {"error": f"Could not read file: {e}"}
        
        language = self._detect_language(filepath)
        patterns = self._get_patterns_for_language(language)
        
        issues = []
        lines = content.split('\n')
        
        # Pattern-based analysis
        for pattern_def in patterns:
            pattern = pattern_def["pattern"]
            for line_num, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    # Check if in ignore patterns
                    if any(re.search(ip, line) for ip in self.settings.get("ignore_patterns", [])):
                        continue
                        
                    issues.append({
                        "rule_id": pattern_def["id"],
                        "message": pattern_def["message"],
                        "severity": pattern_def["severity"],
                        "category": pattern_def["category"],
                        "line": line_num,
                        "code": line.strip()[:100],
                        "suggestion": pattern_def.get("suggestion", "")
                    })
        
        # AST analysis for Python
        if language == 'python':
            ast_issues = self._analyze_python_ast(content, filepath)
            issues.extend(ast_issues)
        
        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        issues.sort(key=lambda x: (severity_order.get(x["severity"], 5), x["line"]))
        
        # Calculate score
        score = 100
        for issue in issues:
            score -= SEVERITY[issue["severity"]]["weight"]
        score = max(0, score)
        
        # Count by severity
        severity_counts = Counter(i["severity"] for i in issues)
        category_counts = Counter(i["category"] for i in issues)
        
        result = {
            "file": str(path.absolute()),
            "language": language,
            "lines": len(lines),
            "issues": issues,
            "issue_count": len(issues),
            "severity_breakdown": dict(severity_counts),
            "category_breakdown": {
                CATEGORIES.get(k, k): v for k, v in category_counts.items()
            },
            "score": score,
            "grade": self._score_to_grade(score),
            "timestamp": datetime.now().isoformat()
        }
        
        # Save to history
        self.history.append({
            "file": str(path),
            "score": score,
            "issues": len(issues),
            "timestamp": result["timestamp"]
        })
        self._save_history()
        
        return result
    
    def _score_to_grade(self, score: int) -> str:
        """Convert score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def review_directory(self, dirpath: str, recursive: bool = True) -> Dict[str, Any]:
        """Review all code files in a directory."""
        path = Path(dirpath)
        
        if not path.exists():
            return {"error": f"Directory not found: {dirpath}"}
        
        if not path.is_dir():
            return {"error": f"Not a directory: {dirpath}"}
        
        # Find code files
        extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.go', '.rs', '.rb', '.php'}
        
        if recursive:
            files = [f for f in path.rglob('*') if f.suffix.lower() in extensions]
        else:
            files = [f for f in path.glob('*') if f.suffix.lower() in extensions]
        
        # Skip common non-code directories
        skip_dirs = {'node_modules', 'venv', '.venv', '__pycache__', '.git', 'dist', 'build'}
        files = [f for f in files if not any(sd in f.parts for sd in skip_dirs)]
        
        if not files:
            return {"error": "No code files found", "directory": str(path)}
        
        results = []
        total_issues = 0
        total_score = 0
        
        for file in files[:50]:  # Limit to 50 files
            result = self.review_file(str(file))
            if "error" not in result:
                results.append(result)
                total_issues += result["issue_count"]
                total_score += result["score"]
        
        avg_score = total_score / len(results) if results else 0
        
        return {
            "directory": str(path.absolute()),
            "files_reviewed": len(results),
            "total_issues": total_issues,
            "average_score": round(avg_score, 1),
            "average_grade": self._score_to_grade(int(avg_score)),
            "file_results": results,
            "summary": self._generate_summary(results),
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_summary(self, results: List[Dict]) -> Dict:
        """Generate summary from multiple file reviews."""
        all_issues = []
        for r in results:
            all_issues.extend(r.get("issues", []))
        
        severity_total = Counter(i["severity"] for i in all_issues)
        category_total = Counter(i["category"] for i in all_issues)
        
        # Find most common issues
        rule_counts = Counter(i["rule_id"] for i in all_issues)
        
        return {
            "total_issues": len(all_issues),
            "by_severity": dict(severity_total),
            "by_category": {
                CATEGORIES.get(k, k): v for k, v in category_total.items()
            },
            "top_issues": [
                {"rule_id": rule, "count": count}
                for rule, count in rule_counts.most_common(5)
            ]
        }
    
    def list_rules(self) -> Dict[str, List[Dict]]:
        """List all available rules."""
        return {
            "python": [
                {
                    "id": p["id"],
                    "severity": p["severity"],
                    "category": CATEGORIES.get(p["category"], p["category"]),
                    "message": p["message"]
                }
                for p in PYTHON_PATTERNS
            ],
            "javascript": [
                {
                    "id": p["id"],
                    "severity": p["severity"],
                    "category": CATEGORIES.get(p["category"], p["category"]),
                    "message": p["message"]
                }
                for p in JS_PATTERNS
            ],
            "generic": [
                {
                    "id": p["id"],
                    "severity": p["severity"],
                    "category": CATEGORIES.get(p["category"], p["category"]),
                    "message": p["message"]
                }
                for p in GENERIC_PATTERNS
            ]
        }
    
    def get_stats(self) -> Dict:
        """Get review statistics."""
        if not self.history:
            return {"total_reviews": 0}
        
        scores = [h["score"] for h in self.history]
        issues = [h["issues"] for h in self.history]
        
        return {
            "total_reviews": len(self.history),
            "average_score": round(sum(scores) / len(scores), 1),
            "total_issues_found": sum(issues),
            "best_score": max(scores),
            "worst_score": min(scores),
            "recent_reviews": self.history[-5:]
        }
    
    def clear_history(self) -> Dict:
        """Clear review history."""
        self.history = []
        self._save_history()
        return {"status": "cleared"}


def format_review_output(result: Dict) -> str:
    """Format review result for terminal output."""
    if "error" in result:
        return f"Error: {result['error']}"
    
    output = []
    output.append(f"\n{'='*60}")
    output.append(f"Code Review: {result.get('file', result.get('directory', 'Unknown'))}")
    output.append(f"{'='*60}")
    
    if "files_reviewed" in result:
        # Directory result
        output.append(f"Files reviewed: {result['files_reviewed']}")
        output.append(f"Total issues: {result['total_issues']}")
        output.append(f"Average score: {result['average_score']}/100 ({result['average_grade']})")
        
        if result.get("summary"):
            output.append(f"\nTop issues:")
            for ti in result["summary"].get("top_issues", []):
                output.append(f"  - {ti['rule_id']}: {ti['count']} occurrences")
    else:
        # Single file result
        output.append(f"Language: {result['language']}")
        output.append(f"Lines: {result['lines']}")
        output.append(f"Score: {result['score']}/100 ({result['grade']})")
        output.append(f"Issues found: {result['issue_count']}")
        
        if result["issues"]:
            output.append(f"\nIssues:")
            for issue in result["issues"]:
                sev = SEVERITY[issue["severity"]]
                output.append(f"  {sev['emoji']} [{issue['rule_id']}] Line {issue['line']}: {issue['message']}")
                if issue.get("code"):
                    output.append(f"     > {issue['code'][:60]}...")
                if issue.get("suggestion"):
                    output.append(f"     Suggestion: {issue['suggestion']}")
    
    output.append(f"{'='*60}\n")
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(
        description="Code Review Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python review_engine.py review -f script.py
  python review_engine.py review -d ./src
  python review_engine.py review -d ./src --json
  python review_engine.py rules
  python review_engine.py stats
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Review command
    review_parser = subparsers.add_parser("review", help="Review code")
    review_parser.add_argument("-f", "--file", help="File to review")
    review_parser.add_argument("-d", "--directory", help="Directory to review")
    review_parser.add_argument("--json", action="store_true", help="Output as JSON")
    review_parser.add_argument("--no-recursive", action="store_true", help="Don't recurse into subdirectories")
    
    # Rules command
    subparsers.add_parser("rules", help="List all rules")
    
    # Stats command
    subparsers.add_parser("stats", help="Show review statistics")
    
    # Clear command
    subparsers.add_parser("clear", help="Clear history")
    
    args = parser.parse_args()
    engine = CodeReviewEngine()
    
    if args.command == "review":
        if args.file:
            result = engine.review_file(args.file)
        elif args.directory:
            result = engine.review_directory(args.directory, recursive=not args.no_recursive)
        else:
            print("Error: Specify -f FILE or -d DIRECTORY")
            return
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(format_review_output(result))
            
    elif args.command == "rules":
        rules = engine.list_rules()
        print(json.dumps(rules, indent=2))
        
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
