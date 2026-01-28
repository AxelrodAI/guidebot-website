# Code Review Assistant

Auto-review code for issues, security concerns, and style problems. Supports Python, JavaScript/TypeScript, and generic pattern matching.

## Features

- **Security scanning** - Detects eval(), hardcoded credentials, injection risks
- **Bug detection** - Mutable defaults, bare excepts, equality issues
- **Style checks** - TODO/FIXME comments, print statements, var vs let/const
- **Complexity analysis** - Function length, branch complexity, argument count
- **Multi-language** - Python, JavaScript, TypeScript, generic patterns
- **AST analysis** - Deep Python analysis using abstract syntax trees
- **Scoring system** - 0-100 score with letter grades (A-F)

## CLI Usage

```bash
# Review a single file
python review_engine.py review -f script.py

# Review a directory (recursive)
python review_engine.py review -d ./src

# Non-recursive directory review
python review_engine.py review -d ./src --no-recursive

# Output as JSON
python review_engine.py review -f script.py --json

# List all rules
python review_engine.py rules

# View statistics
python review_engine.py stats

# Clear history
python review_engine.py clear
```

## Example Output

```
============================================================
Code Review: /path/to/script.py
============================================================
Language: python
Lines: 150
Score: 75/100 (C)
Issues found: 5

Issues:
  🔴 [PY001] Line 23: Use of eval() is dangerous - can execute arbitrary code
     > result = eval(user_input)
     Suggestion: Use ast.literal_eval() for safe evaluation of literals

  🟠 [PY022] Line 45: Mutable default argument (list)
     > def process(items=[]):
     Suggestion: Use None as default, initialize in function body

  🟡 [PY020] Line 67: Bare except catches all exceptions
     > except:
     Suggestion: Use 'except Exception:' or specific exceptions

  🟢 [PY024] Line 89: Use 'is None' instead of '== None'
     > if result == None:
     Suggestion: if x is None:

  ℹ️ [PY033] Line 12: Print statement found
     > print("Debug:", data)
     Suggestion: Use logging module for production code
============================================================
```

## Severity Levels

| Level | Emoji | Impact |
|-------|-------|--------|
| Critical | 🔴 | Security vulnerabilities, crashes |
| High | 🟠 | Likely bugs, security concerns |
| Medium | 🟡 | Code quality issues |
| Low | 🟢 | Style suggestions |
| Info | ℹ️ | Informational notes |

## Categories

- 🔒 **Security** - Vulnerabilities and injection risks
- ⚡ **Performance** - Inefficient patterns
- 🎨 **Style** - Code style and formatting
- 🐛 **Potential Bug** - Likely runtime issues
- 🔄 **Complexity** - Overly complex code
- 📚 **Maintainability** - Technical debt
- ✅ **Best Practice** - Industry standards

## Python Rules

| ID | Issue | Severity |
|----|-------|----------|
| PY001 | eval() usage | Critical |
| PY002 | exec() usage | Critical |
| PY003 | Pickle deserialization | High |
| PY004 | os.system() shell injection | High |
| PY005 | subprocess shell=True | High |
| PY006 | Hardcoded credentials | Critical |
| PY020 | Bare except | Medium |
| PY022 | Mutable default (list) | High |
| PY023 | Mutable default (dict) | High |
| PY024 | == None instead of is None | Low |
| AST001 | High cyclomatic complexity | Medium |
| AST002 | Function too long | Low |
| AST003 | Too many arguments | Low |

## JavaScript Rules

| ID | Issue | Severity |
|----|-------|----------|
| JS001 | eval() usage | Critical |
| JS002 | innerHTML XSS risk | High |
| JS003 | document.write() | High |
| JS004 | Sensitive data in localStorage | High |
| JS010 | var instead of let/const | Low |
| JS011 | == instead of === | Medium |
| JS012 | != instead of !== | Medium |
| JS013 | console.log statements | Info |
| JS014 | debugger statement | Medium |

## API (Python)

```python
from review_engine import CodeReviewEngine

engine = CodeReviewEngine()

# Review a file
result = engine.review_file("script.py")
print(f"Score: {result['score']}/100 ({result['grade']})")
print(f"Issues: {result['issue_count']}")

for issue in result['issues']:
    print(f"  Line {issue['line']}: {issue['message']}")

# Review a directory
result = engine.review_directory("./src")
print(f"Average score: {result['average_score']}")
```

## Scoring

- Start with 100 points
- Deductions per issue:
  - Critical: -10
  - High: -5
  - Medium: -3
  - Low: -1
  - Info: 0

## Files

- `review_engine.py` - Main engine with CLI
- `README.md` - This documentation
- `data/` - Review history and settings

## Integration Ideas

- Git pre-commit hook
- CI/CD pipeline step
- IDE plugin
- Code review bot
