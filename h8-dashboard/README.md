# 📊 H.8 Banking Dashboard

A live public dashboard for Federal Reserve H.8 (Assets and Liabilities of Commercial Banks) data.

## Features

- **Real-time Data Display**: Latest values for loans, deposits, and bank credit
- **Quarter-to-Date Growth Charts**: Compare current quarter to same quarter in past 5 years
- **YoY Trends**: Track year-over-year changes over time
- **Dark Theme**: Professional fintech-style dark theme
- **Mobile Responsive**: Works on all devices

## H.8 Release Schedule

The Federal Reserve releases H.8 data:
- **When**: Every Friday at 4:15 PM ET
- **Data As-Of**: The prior Wednesday
- **Example**: Data released Jan 31, 2025 reflects balances as of Jan 29, 2025

## Setup

### 1. Get a FRED API Key (Free)

1. Go to https://fred.stlouisfed.org/docs/api/api_key.html
2. Click "Request or view your API keys"
3. Create a free account or sign in
4. Request an API key

### 2. Configure the API Key

Set the environment variable:
```bash
# Windows (PowerShell)
$env:FRED_API_KEY = "your_key_here"

# Windows (CMD)
set FRED_API_KEY=your_key_here

# Linux/Mac
export FRED_API_KEY=your_key_here
```

Or create a `.env` file in this directory:
```
FRED_API_KEY=your_key_here
```

### 3. Install Dependencies

```bash
pip install fredapi pandas
```

### 4. Generate Data

```bash
python h8_data_updater.py
```

This creates `h8_data.json` which the dashboard reads.

### 5. View Dashboard

Open `index.html` in a browser, or serve it:
```bash
# Python 3
python -m http.server 8000

# Then open: http://localhost:8000
```

## Auto-Updates

### Option 1: GitHub Actions (Recommended)

Add this workflow to `.github/workflows/update-h8.yml`:

```yaml
name: Update H.8 Data

on:
  schedule:
    # Run every Friday at 4:30 PM ET (21:30 UTC)
    - cron: '30 21 * * 5'
  workflow_dispatch: # Manual trigger

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install fredapi pandas
      
      - name: Update H.8 data
        env:
          FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
        run: python h8-dashboard/h8_data_updater.py
      
      - name: Commit and push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add h8-dashboard/h8_data.json
          git diff --staged --quiet || git commit -m "Update H.8 data [automated]"
          git push
```

Add `FRED_API_KEY` to your repository secrets.

### Option 2: Windows Task Scheduler

Create a scheduled task to run `h8_data_updater.py` every Friday evening.

## Files

| File | Description |
|------|-------------|
| `index.html` | The dashboard webpage |
| `h8_data.json` | Cached data (auto-generated) |
| `h8_data_updater.py` | Python script to fetch data from FRED |

## Data Series

| Series ID | Name | Category |
|-----------|------|----------|
| TOTLL | Total Loans & Leases | Loans |
| TOTCI | C&I Loans | Loans |
| RELACBW027SBOG | Real Estate Loans | Loans |
| CLSACBW027SBOG | Consumer Loans | Loans |
| DPSACBW027SBOG | Total Deposits | Deposits |
| LTDACBW027SBOG | Large Time Deposits | Deposits |
| TOTBKCR | Total Bank Credit | Other |
| SBCACBW027SBOG | Securities | Other |
| CASACBW027SBOG | Cash Assets | Other |

## Data Source

Federal Reserve H.8 Release: https://www.federalreserve.gov/releases/h8/

Data accessed via FRED API: https://fred.stlouisfed.org/
