# Auto-Updating Dashboard Builder

A powerful, no-code dashboard builder that generates self-refreshing HTML dashboards for real-time data visualization.

## Features

### 🎨 Widget Library
- **Metric Cards** - KPI displays with trend indicators
- **Line Charts** - Time-series data visualization
- **Bar Charts** - Comparative data analysis
- **Pie/Doughnut Charts** - Distribution breakdowns
- **Data Tables** - Sortable, filterable tabular data
- **Activity Feeds** - Real-time event streams

### ⏱️ Auto-Refresh System
- Configurable refresh intervals (5s to 5min)
- Visual countdown timer with progress ring
- Live indicator showing connection status
- Smooth data transitions without page reload
- Flash effects on updated widgets

### 🔗 Data Sources
- REST API integration
- WebSocket connections
- Database queries
- JSON file imports
- Custom data adapters

### 📦 Templates
- **Sales Dashboard** - Revenue, conversions, pipeline
- **DevOps Monitor** - Server health, deployments, alerts
- **Social Analytics** - Engagement, followers, reach

### 💾 Export Options
- **Standalone HTML** - Self-contained file with embedded refresh
- **JSON Config** - Dashboard configuration for sharing
- **Embed Code** - iFrame snippet for websites
- **Share Link** - Hosted dashboard URL

## Usage

1. **Open** `index.html` in your browser
2. **Drag widgets** from the sidebar to the dashboard grid
3. **Configure** data sources via the settings panel (⚙️)
4. **Set refresh interval** using the dropdown selector
5. **Watch** data auto-update at the configured interval
6. **Export** your dashboard for deployment

## Technical Details

- Built with vanilla JavaScript + Chart.js
- No backend required for demo mode
- Simulated data updates for demonstration
- Responsive design (desktop, tablet, mobile)
- Dark theme with gradient background

## Configuration API

```javascript
// Dashboard configuration structure
{
  "name": "My Dashboard",
  "refreshInterval": 30,
  "widgets": [
    {
      "type": "metric",
      "title": "Total Users",
      "dataSource": "/api/users/count",
      "format": "number"
    },
    {
      "type": "line-chart",
      "title": "Traffic Over Time",
      "dataSource": "/api/analytics/traffic",
      "size": "large"
    }
  ],
  "dataSources": {
    "rest": {
      "baseUrl": "https://api.example.com",
      "auth": "bearer",
      "token": "xxx"
    }
  }
}
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `R` | Force refresh |
| `E` | Export dashboard |
| `S` | Toggle settings |
| `N` | Add new widget |

## Future Enhancements

- [ ] Drag-and-drop widget reordering
- [ ] Custom widget sizing
- [ ] Multiple dashboard tabs
- [ ] Real-time collaboration
- [ ] Alert thresholds and notifications
- [ ] Historical data comparisons
- [ ] PDF report generation

---

Built by PM2 | Auto-Updating Dashboards (Idea #22)
