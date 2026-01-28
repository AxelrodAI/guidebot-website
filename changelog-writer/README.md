# Automated Changelog Writer

Generate professional changelogs from git commits with Conventional Commits support.

## Features

- **Conventional Commits** - Automatic parsing of `type(scope): subject` format
- **Smart Categorization** - Groups commits by type (features, fixes, docs, etc.)
- **Keep a Changelog** - Follows the standard changelog format
- **Breaking Changes** - Highlights breaking changes prominently
- **Issue Linking** - Auto-detects `closes #123` references
- **Statistics** - Commit metrics and contributor stats
- **Validation** - Check commit message compliance
- **Visual Dashboard** - Browser-based generator

## Installation

No dependencies required (Python 3.7+ with git).

```bash
cd changelog-writer
```

## Quick Start

### Generate Changelog

```bash
# Generate from recent commits
python changelog_gen.py generate

# Generate for specific version
python changelog_gen.py generate --version 1.0.0 --date 2025-01-27

# Generate since last tag
python changelog_gen.py generate --since v0.9.0
```

### Preview Commits

```bash
# See how commits will be parsed
python changelog_gen.py preview --commits 20
```

### Release New Version

```bash
# Create a new version release
python changelog_gen.py release 1.0.0

# With custom date
python changelog_gen.py release 1.0.0 --date 2025-01-27
```

### Validate Commits

```bash
# Check Conventional Commits compliance
python changelog_gen.py validate
```

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `generate` | Generate changelog content | `generate --since v1.0.0` |
| `preview` | Preview parsed commits | `preview --commits 20` |
| `version` | Generate for specific version | `version 1.0.0` |
| `init` | Initialize CHANGELOG.md | `init --format keep` |
| `validate` | Check commit format | `validate` |
| `stats` | Show commit statistics | `stats --since v1.0.0` |
| `unreleased` | Show unreleased changes | `unreleased` |
| `release` | Create new version | `release 1.0.0` |

All commands support `--json` for machine-readable output.

## Conventional Commits

The tool understands Conventional Commits format:

```
<type>(<scope>)!: <subject>

[body]

[footer]
```

### Types

| Type | Description | Emoji |
|------|-------------|-------|
| `feat` | New feature | ✨ |
| `fix` | Bug fix | 🐛 |
| `docs` | Documentation | 📚 |
| `style` | Formatting | 💄 |
| `refactor` | Code refactoring | ♻️ |
| `perf` | Performance | ⚡ |
| `test` | Tests | ✅ |
| `build` | Build system | 📦 |
| `ci` | CI/CD | 👷 |
| `chore` | Maintenance | 🔧 |

### Breaking Changes

Mark with `!` or `BREAKING CHANGE` in body:

```
feat!: remove deprecated API endpoint

# or

feat(api): change response format

BREAKING CHANGE: Response now returns array instead of object
```

### Issue References

Automatically detected:

```
fix: resolve login issue

Closes #123
Fixes #456
```

## Example Output

```markdown
## [1.0.0] - 2025-01-27

### 💥 Breaking Changes

- **api**: Change response format ([abc123](https://github.com/user/repo/commit/abc123))

### ✨ Features

- **auth**: Add OAuth2 authentication support ([def456](https://github.com/user/repo/commit/def456))
- **ui**: New dashboard with real-time updates ([ghi789](https://github.com/user/repo/commit/ghi789))

### 🐛 Bug Fixes

- Resolve memory leak in connection pool ([jkl012](https://github.com/user/repo/commit/jkl012))
- **auth**: Fix token refresh race condition (#123) ([mno345](https://github.com/user/repo/commit/mno345))

### 📚 Documentation

- Update API documentation with examples ([pqr678](https://github.com/user/repo/commit/pqr678))
```

## Configuration

Create `changelog.config.json`:

```json
{
  "format": "keep",
  "include_commits": true,
  "include_authors": false,
  "include_links": true,
  "repo_url": "https://github.com/user/repo",
  "types": ["feat", "fix", "docs", "perf", "refactor"],
  "header": "# Changelog\n\nAll notable changes..."
}
```

### Options

| Option | Type | Description |
|--------|------|-------------|
| `format` | string | "keep" or "simple" |
| `include_commits` | bool | Show commit hashes |
| `include_authors` | bool | Show commit authors |
| `include_links` | bool | Link to commits |
| `repo_url` | string | Repository URL for links |
| `types` | array | Types to include |

## Dashboard

Open `index.html` for a visual interface:

- Parse commits interactively
- Preview categorization
- Generate formatted changelog
- Copy to clipboard
- Paste raw commit messages

## Statistics

```bash
python changelog_gen.py stats

# Output:
📊 COMMIT STATISTICS (all time)
   Total commits: 150
   Features: 45
   Bug fixes: 38
   Breaking changes: 3

   By type:
      ✨ feat: 45
      🐛 fix: 38
      📚 docs: 25
      ♻️ refactor: 20

   Top contributors:
      👤 John: 65
      👤 Jane: 50
```

## Workflow Integration

### Pre-Release Check

```bash
# Validate commits before release
python changelog_gen.py validate
if [ $? -eq 0 ]; then
    python changelog_gen.py release 1.0.0
fi
```

### CI/CD

```yaml
# GitHub Actions
- name: Generate Changelog
  run: |
    python changelog_gen.py release ${{ github.ref_name }}
    cat CHANGELOG.md
```

### Git Hook

```bash
# .git/hooks/commit-msg
python changelog_gen.py validate --commits 1
```

## Fallback Parsing

Non-conventional commits are auto-categorized:

| Starts with | Type |
|-------------|------|
| `add`, `new`, `create`, `implement` | feat |
| `fix`, `bug`, `patch`, `resolve` | fix |
| `doc`, `readme`, `comment` | docs |
| `refactor`, `clean`, `reorganize` | refactor |
| `test`, `spec` | test |

## Tips

1. **Use Conventional Commits** - Better parsing and categorization
2. **Include scope** - Helps group related changes
3. **Reference issues** - Auto-links to issue tracker
4. **Mark breaking changes** - Prominently displayed
5. **Run validate** - Before release to check compliance

## Limitations

- Requires git repository
- English commit messages work best
- Complex merge commits may not parse perfectly

## Contributing

Part of the Guidebot feature pipeline. Improvements welcome!

## License

MIT
