# Project Health Dashboard

A comprehensive project health monitoring dashboard that aggregates repository, ticket, and deployment metrics into a single unified view.

## Features

### 🏥 Health Score
- **Composite Score (0-100)** - Overall project health rating
- **Visual Ring Indicator** - Animated progress ring
- **Health Status** - Healthy / Warning / Critical
- **Trend Tracking** - Week-over-week comparison

### 📊 Health Breakdown
- **Code Quality** - Lint scores, complexity metrics
- **Test Coverage** - Percentage of code tested
- **Issue Velocity** - Issue close rate vs open rate
- **Deploy Success** - Deployment success percentage

### 📈 Key Metrics
- **Open Issues** - Current backlog count
- **Open PRs** - Pending pull requests
- **Commits** - Activity over time period
- **Deploys** - Deployment frequency

### 📉 Charts & Visualizations
- **Activity Trend** - Line chart of commits, PRs merged, issues closed
- **Issue Distribution** - Doughnut chart by type (Bug, Feature, Enhancement, etc.)

### 🚨 Critical Alerts
- **Critical Issues** - High priority bugs requiring attention
- **Stale Issues** - Issues open too long
- **Pending PRs** - Pull requests awaiting review

### 👥 Team Activity
- **Contributor Cards** - Top contributors with commit/PR counts
- **Activity Rankings** - Most active team members

### 🚀 Deployment History
- **Recent Deploys** - Timeline of deployments
- **Environment Tags** - Production, Staging, Dev
- **Status Indicators** - Success, Failed, Pending
- **Version Tracking** - Release versioning

## Usage

1. **Open** `index.html` in your browser
2. **Select Project** from the dropdown
3. **Choose Time Range** (24h, 7d, 30d, 90d)
4. **Monitor** health score and metrics
5. **Click Refresh** to update data

## Data Sources

Integrates with:
- GitHub / GitLab / Bitbucket (repos)
- Jira / Linear / GitHub Issues (tickets)
- Jenkins / GitHub Actions / CircleCI (CI/CD)
- SonarQube / CodeClimate (code quality)

## Health Score Calculation

```
Health Score = (
  Code Quality × 0.25 +
  Test Coverage × 0.25 +
  Issue Velocity × 0.25 +
  Deploy Success × 0.25
)
```

### Thresholds
| Score | Status | Color |
|-------|--------|-------|
| 80-100 | Healthy | Green |
| 60-79 | Warning | Yellow |
| 0-59 | Critical | Red |

## API Configuration

```javascript
// config.js
const config = {
  github: {
    token: 'ghp_xxx',
    repo: 'owner/repo'
  },
  jira: {
    url: 'https://company.atlassian.net',
    project: 'PROJ'
  },
  cicd: {
    provider: 'github-actions'
  }
};
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `R` | Refresh data |
| `1-4` | Switch time range |
| `P` | Cycle projects |

## Future Enhancements

- [ ] Real-time WebSocket updates
- [ ] Custom alert thresholds
- [ ] Slack/Discord notifications
- [ ] Historical trend analysis
- [ ] Export to PDF reports
- [ ] Team velocity tracking
- [ ] Sprint burndown charts

---

Built by PM2 | Project Health Dashboard (Idea #108)
