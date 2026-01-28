# Codebase Documentation Generator 📚

> Auto-generate comprehensive documentation from repository analysis. Turn any codebase into well-structured docs in seconds.

## Overview

This tool analyzes your codebase and automatically generates:
- **README.md** - Project overview with structure, stats, and key files
- **API Reference** - Function and class documentation extracted from code
- **Project Structure** - Visual tree of your repository
- **Statistics** - Line counts, language breakdown, complexity metrics

## Quick Start

### Dashboard UI

Open `index.html` in your browser for the visual interface:

```bash
# Windows
start index.html

# Mac
open index.html

# Linux
xdg-open index.html
```

### Python CLI

```bash
# Analyze a codebase
python doc_generator.py analyze -d /path/to/project

# Generate full documentation
python doc_generator.py generate -d /path/to/project -o docs

# Show project structure
python doc_generator.py structure -d /path/to/project

# Show statistics
python doc_generator.py stats -d /path/to/project

# Extract functions from a file
python doc_generator.py functions -f main.py

# Generate just README
python doc_generator.py readme -d /path/to/project --preview
```

## Features

### 1. Multi-Language Support

Analyzes code in 16+ languages:
- **Python** - Full AST analysis (classes, functions, docstrings, imports)
- **JavaScript/TypeScript** - Functions, classes, React components
- **Java, C++, C, Go, Rust** - Basic structure extraction
- **And more** - Ruby, PHP, Swift, Kotlin, C#, Scala

### 2. Code Analysis

For Python files, extracts:
- Module docstrings
- Class definitions with methods
- Function signatures with arguments
- Type hints and return types
- Decorators
- Import statements
- Constants (UPPER_CASE)

For JavaScript/TypeScript:
- Import/export statements
- Function definitions (regular and arrow)
- Class definitions with inheritance
- React component detection

### 3. Statistics Dashboard

Calculates:
- Total files, lines, and code lines
- Comment ratio and documentation coverage
- Average lines per file
- Language breakdown with percentages
- Largest files by code lines

### 4. Project Structure

Generates visual tree with:
- Directory hierarchy
- File type icons (🐍 Python, 📜 JS/TS, 📄 others)
- Configurable depth
- Auto-ignores common directories (node_modules, .git, __pycache__)

### 5. Documentation Generation

**README.md** includes:
- Overview table with key metrics
- Language breakdown
- Project structure tree
- Key file summaries
- Dependency information

**API Reference** includes:
- Module documentation
- Class definitions with methods
- Function signatures
- Docstrings and type hints

## CLI Reference

### `analyze`

Analyze a codebase and display summary.

```bash
python doc_generator.py analyze -d /path/to/project [-o output.json]
```

Options:
- `-d, --directory` - Directory to analyze (required)
- `-o, --output` - Save analysis to JSON file

### `generate`

Generate full documentation suite.

```bash
python doc_generator.py generate -d /path/to/project -o docs
```

Options:
- `-d, --directory` - Directory to analyze (required)
- `-o, --output` - Output directory (default: docs)

Creates:
- `docs/README.md` - Project overview
- `docs/API.md` - API reference
- `docs/analysis.json` - Raw analysis data

### `structure`

Display project structure as tree.

```bash
python doc_generator.py structure -d /path/to/project [--depth 4]
```

Options:
- `-d, --directory` - Directory (required)
- `--depth` - Max depth to traverse (default: 4)

### `stats`

Show detailed codebase statistics.

```bash
python doc_generator.py stats -d /path/to/project
```

Displays:
- Overall metrics (files, lines, size)
- Comment ratio
- Language breakdown with visual bars
- Top 10 largest files

### `functions`

Extract functions and classes from a single file.

```bash
python doc_generator.py functions -f main.py
```

Shows:
- Module docstring
- Classes with methods
- Functions with arguments
- Docstrings (truncated)

### `readme`

Generate README.md for a project.

```bash
python doc_generator.py readme -d /path/to/project [-o README.md] [--preview]
```

Options:
- `-d, --directory` - Directory (required)
- `-o, --output` - Output file (default: README.generated.md)
- `--preview` - Show preview in terminal

## Configuration

### Ignored Directories

By default, these directories are skipped:
- `.git`
- `node_modules`
- `__pycache__`
- `.venv`, `venv`, `env`
- `dist`, `build`
- `.next`, `.cache`
- `coverage`
- `.idea`, `.vscode`

### Supported Extensions

| Extension | Language |
|-----------|----------|
| .py | Python |
| .js | JavaScript |
| .ts | TypeScript |
| .jsx | React JSX |
| .tsx | React TSX |
| .java | Java |
| .cpp, .c | C/C++ |
| .h, .hpp | Headers |
| .go | Go |
| .rs | Rust |
| .rb | Ruby |
| .php | PHP |
| .swift | Swift |
| .kt | Kotlin |
| .cs | C# |
| .scala | Scala |

## Example Output

### Generated README.md

```markdown
# Project Documentation

> Auto-generated documentation for `my-project`

## Overview

| Metric | Value |
|--------|-------|
| Total Files | 45 |
| Total Lines | 8,234 |
| Code Lines | 6,891 |
| Size | 312.5 KB |

## Languages

| Language | Files | Lines |
|----------|-------|-------|
| Python | 28 | 5,400 |
| JavaScript | 12 | 2,100 |
| TypeScript | 5 | 734 |

...
```

### Statistics Output

```
📊 CODEBASE STATISTICS
==================================================

📈 OVERALL:
   Files: 45
   Lines: 8,234
   Code Lines: 6,891
   Comment Ratio: 16.3%
   Avg Lines/File: 183

🗣️ BY LANGUAGE:
   Python          ████████████████░░░░ 65.6% (28 files)
   JavaScript      ██████░░░░░░░░░░░░░░ 25.5% (12 files)
   TypeScript      ██░░░░░░░░░░░░░░░░░░  8.9% (5 files)
```

## Integration

### Voice Commands (Clawdbot)

Say to Clawdbot:
- "Document my project at C:\Users\me\project"
- "Generate API docs for the backend"
- "Show me the structure of my codebase"
- "What's the language breakdown of this repo?"
- "Extract functions from main.py"

### CI/CD Pipeline

Add to your CI workflow:
```yaml
- name: Generate Documentation
  run: |
    python doc_generator.py generate -d . -o docs
    git add docs/
    git commit -m "Update auto-generated docs"
```

### Pre-commit Hook

Auto-update docs on commit:
```bash
#!/bin/sh
python doc_generator.py readme -d . -o README.generated.md
git add README.generated.md
```

## Roadmap

- [x] Python AST analysis
- [x] JavaScript/TypeScript support
- [x] Dashboard UI
- [x] CLI with multiple commands
- [ ] JSDoc/TSDoc parsing
- [ ] Rust/Go deep analysis
- [ ] Diagram generation (mermaid)
- [ ] Git history integration
- [ ] Complexity metrics (cyclomatic)
- [ ] Test coverage integration

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                Codebase Documentation Generator               │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐        │
│  │   Python    │   │ JavaScript  │   │   Generic   │        │
│  │   Analyzer  │   │  Analyzer   │   │  Analyzer   │        │
│  │   (AST)     │   │  (Regex)    │   │ (Line cnt)  │        │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘        │
│         │                 │                 │                │
│         └────────────┬────┴─────────────────┘                │
│                      ▼                                        │
│         ┌────────────────────────┐                           │
│         │    Analysis Engine     │                           │
│         │  - File traversal      │                           │
│         │  - Stats calculation   │                           │
│         │  - Structure mapping   │                           │
│         └───────────┬────────────┘                           │
│                     ▼                                        │
│         ┌────────────────────────┐                           │
│         │   Documentation Gen    │                           │
│         │  - README.md           │                           │
│         │  - API.md              │                           │
│         │  - analysis.json       │                           │
│         └────────────────────────┘                           │
│                                                               │
│  ┌────────────────┐        ┌────────────────┐               │
│  │  Dashboard UI  │        │   CLI Output   │               │
│  │  (index.html)  │        │   (terminal)   │               │
│  └────────────────┘        └────────────────┘               │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

## License

MIT License - Part of Clawdbot project.

---

*Generated documentation is only as good as your code comments! Write good docstrings.* 📝
