# Test Coverage Visualizer

Visual coverage reports with actionable suggestions for improving test coverage.

## Features

### Coverage Summary
- **Overall Coverage** - Combined score
- **Line Coverage** - Lines executed by tests
- **Branch Coverage** - Decision paths tested
- **Function Coverage** - Functions called
- **Files Covered** - File count with tests

Color-coded thresholds:
- 🟢 Excellent: ≥90%
- 🟡 Good: ≥75%
- 🟠 Warning: ≥50%
- 🔴 Poor: <50%

### File Tree Browser
- Hierarchical folder/file view
- Per-file coverage percentage
- Visual coverage bars
- Search/filter functionality
- Click to select and drill down

### Coverage Suggestions
AI-powered improvement recommendations:
- **High Priority** - Critical untested code
- **Medium Priority** - Important gaps
- **Low Priority** - Nice-to-have tests

Each suggestion includes:
- Description of what's missing
- Specific file path
- Improvement guidance

### Coverage by Type Chart
Doughnut chart showing:
- Lines coverage
- Branches coverage
- Functions coverage
- Statements coverage

### Coverage Trend
- Historical coverage over time
- Weekly/monthly improvement tracking
- Tests run count
- Failure tracking

### Uncovered Code Preview
- Syntax-highlighted code blocks
- Green = covered lines
- Red = uncovered lines
- Line numbers

## Usage

1. Open `index.html` in browser
2. View summary metrics at top
3. Browse file tree to find low-coverage files
4. Read suggestions for improvement priorities
5. Check trend chart for progress tracking
6. Review uncovered code samples

## Report Upload
Supports coverage report formats:
- lcov (LCOV format)
- Istanbul/nyc JSON
- Cobertura XML
- Jest coverage output

## Integration Ready
Connect with:
- GitHub Actions coverage reports
- CI/CD pipelines
- Pre-commit hooks
- Pull request checks

Built by PM2 for the Clawdbot pipeline.
