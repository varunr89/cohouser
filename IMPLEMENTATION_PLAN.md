# Wild Whatcom Financial Dashboard - Complete Implementation Plan

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture & Technology Decisions](#architecture--technology-decisions)
3. [Project Structure](#project-structure)
4. [Implementation Steps](#implementation-steps)
5. [Data Processing Pipeline](#data-processing-pipeline)
6. [React Application Components](#react-application-components)
7. [Styling & Design System](#styling--design-system)
8. [Deployment Configuration](#deployment-configuration)
9. [Testing & Validation](#testing--validation)
10. [Verification Checklist](#verification-checklist)

---

## Project Overview

### Goal
Create an interactive financial dashboard for Wild Whatcom nonprofit that:
- Displays comprehensive financial health metrics
- Uses static data (pre-processed from CSV to JSON)
- Provides drill-down navigation from high-level to detailed views
- Includes Sankey diagrams for money flow visualization
- Is accessible to non-technical users
- Deploys automatically to GitHub Pages

### Key Requirements
1. ✅ Static website (client-side only, no server)
2. ✅ Data processing via one-command Python script
3. ✅ Interactive visualizations (Plotly.js)
4. ✅ 5-level drill-down structure
5. ✅ GitHub Actions for automated deployment
6. ✅ Mobile-responsive design

---

## Architecture & Technology Decisions

### Frontend Stack
- **Framework**: React 18.2.0 (component-based architecture)
- **Build Tool**: Vite 5.1.0 (fast dev server, optimized production builds)
- **Routing**: React Router DOM 6.22.0 (client-side navigation)
- **Visualizations**: Plotly.js 2.29.1 + react-plotly.js 2.6.0 (interactive charts)
- **Styling**: Pure CSS with CSS variables (no framework dependencies)

### Data Processing Stack
- **Language**: Python 3.11+
- **Libraries**: Pandas 2.3.3, NumPy 2.3.5
- **Input**: CSV files from `data/wild_whatcom_finance/`
- **Output**: Static JSON files in `public/data/`

### Deployment
- **Hosting**: GitHub Pages (static site hosting)
- **CI/CD**: GitHub Actions workflow
- **Build Process**: Automated on push to `main` or `claude/*` branches

### Why These Choices?
1. **React + Vite**: Modern, fast, great developer experience
2. **Static JSON**: No database needed, fast loading, works on GitHub Pages
3. **Plotly.js**: Rich interactive charts with minimal code
4. **Python**: Excellent CSV processing with Pandas
5. **GitHub Actions**: Free, integrated, automatic deployments

---

## Project Structure

```
wild-whatcom-dashboard/
├── .github/
│   └── workflows/
│       └── deploy.yml                 # GitHub Actions deployment workflow
│
├── public/
│   └── data/                          # Generated JSON files (git-ignored)
│       ├── executive_summary.json
│       ├── historical_trends.json
│       ├── revenue_data.json
│       ├── expense_data.json
│       ├── program_data.json
│       ├── cashflow_data.json
│       └── sankey_data.json
│
├── scripts/
│   └── process_data.py                # CSV to JSON converter
│
├── src/
│   ├── components/                    # Reusable React components
│   │   ├── KPICard.jsx               # Key performance indicator cards
│   │   └── SankeyChart.jsx           # Sankey diagram component
│   │
│   ├── pages/                         # Dashboard pages (routes)
│   │   ├── ExecutiveSummary.jsx      # Main landing page
│   │   ├── RevenuePage.jsx           # Revenue deep dive
│   │   ├── ExpensePage.jsx           # Expense analysis
│   │   ├── CashFlowPage.jsx          # Cash flow & reserves
│   │   └── ProgramsPage.jsx          # Programs & planning
│   │
│   ├── App.jsx                        # Main app component with routing
│   ├── App.css                        # Global styles
│   └── main.jsx                       # React entry point
│
├── .gitignore                         # Git ignore rules
├── index.html                         # HTML entry point
├── package.json                       # Node dependencies
├── vite.config.js                     # Vite configuration
└── README.md                          # User documentation
```

---

## Implementation Steps

### Step 1: Create Project Directory Structure

```bash
# Create main project folder
mkdir -p wild-whatcom-dashboard

# Create subdirectories
mkdir -p wild-whatcom-dashboard/src/{components,pages,utils,assets}
mkdir -p wild-whatcom-dashboard/public/data
mkdir -p wild-whatcom-dashboard/scripts
mkdir -p wild-whatcom-dashboard/.github/workflows
```

### Step 2: Create Configuration Files

#### 2.1 `package.json`

```json
{
  "name": "wild-whatcom-dashboard",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "process-data": "python scripts/process_data.py"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.22.0",
    "plotly.js": "^2.29.1",
    "react-plotly.js": "^2.6.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.55",
    "@types/react-dom": "^18.2.19",
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.1.0"
  }
}
```

**Key Points**:
- `"type": "module"` enables ES6 imports
- `process-data` script for easy data processing
- React 18.2.0 for modern React features
- Vite for fast dev/build

#### 2.2 `vite.config.js`

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/cohouser/',  // IMPORTANT: Match your GitHub repo name
  build: {
    outDir: 'dist',
  },
})
```

**Critical Configuration**:
- `base: '/cohouser/'` - Must match GitHub Pages path
- Without this, routing and asset loading will fail on GitHub Pages

#### 2.3 `index.html`

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Wild Whatcom Financial Dashboard</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

#### 2.4 `.gitignore`

```gitignore
# Dependencies
node_modules
dist
dist-ssr
*.local

# Editor
.vscode/*
!.vscode/extensions.json
.idea
.DS_Store

# Python
__pycache__/
*.py[cod]
.Python
venv/
ENV/

# Generated data (important - don't commit JSON files)
public/data/*.json

# OS
Thumbs.db
```

**Critical**: `public/data/*.json` prevents committing generated files

---

## Data Processing Pipeline

### Step 3: Create Data Processing Script

File: `scripts/process_data.py`

#### 3.1 Script Structure

```python
#!/usr/bin/env python3
"""
Wild Whatcom Financial Data Processing Script
Reads CSV files and generates static JSON files for the dashboard
"""

import pandas as pd
import json
from pathlib import Path
import numpy as np

# Paths (relative to script location)
DATA_DIR = Path(__file__).parent.parent.parent / 'data' / 'wild_whatcom_finance'
OUTPUT_DIR = Path(__file__).parent.parent / 'public' / 'data'
```

#### 3.2 Helper Functions

```python
def clean_currency(value):
    """Convert currency strings to float, handle errors"""
    if pd.isna(value):
        return 0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Handle Excel errors like #REF!
        if value.startswith('#') or value == '':
            return 0
        cleaned = value.replace('$', '').replace(',', '').strip()
        return float(cleaned) if cleaned else 0
    return 0

def safe_float(value):
    """Safely convert to float, handling errors"""
    if pd.isna(value):
        return 0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.startswith('#'):
        return 0
    try:
        return float(value)
    except:
        return 0

def safe_divide(numerator, denominator):
    """Safely divide, returning 0 if denominator is 0"""
    if denominator == 0:
        return 0
    return numerator / denominator
```

**Why These Functions?**:
- Excel exports often contain `#REF!`, `#DIV/0!` errors
- Missing data (NaN) needs consistent handling
- Division by zero protection prevents crashes

#### 3.3 Data Loading Functions

**Key CSV Files and Row/Column Mappings**:

1. **Summary CSV** (`Updated WW Long term financial planning FY19-FY25 - Summary.csv`)
   - Row 3 (index 2): FY26 projected income
   - Row 4 (index 3): FY26 projected expenses
   - Rows 18-23 (indices 17-22): Revenue by category
   - Rows 11-12 (indices 10-11): Expense categories
   - **Column mapping**: Col 2 = FY19, Col 3 = FY20, ..., Col 12 = FY29

2. **FY26 Annual CSV** (`FY 26 Cash Flow Projections (budget+actuals) - Annual.csv`)
   - Rows 7-13 (indices 6-12): Revenue categories
   - Rows 17-20 (indices 16-19): Expense categories
   - Rows 62-67 (indices 61-66): Reserve data
   - Column 2: Budget, Column 3: Actual, Column 5: FY25 Actual

3. **Program Data CSV** (`FY 26 Cash Flow Projections (budget+actuals) - high level Income review.csv`)
   - Row 3 (index 2): Explorers Club
   - Row 4 (index 3): Community
   - Row 5 (index 4): School
   - Row 6 (index 5): Nature Preschool
   - Row 8 (index 7): Camps

4. **Monthly Cashflow CSV** (`FY 26 Cash Flow Projections (budget+actuals) - R + E by monthyear.csv`)
   - Columns 3-14: Sept-Aug monthly data
   - Row 14 (index 13): Total revenue
   - Row 56 (index 55): Total expenses
   - Row 58 (index 57): Net income
   - Row 67 (index 66): Reserves
   - Row 68 (index 67): Months in reserve (if exists)

**Critical**: Pandas uses 0-based indexing after removing header row

#### 3.4 Data Transformation Logic

```python
def load_summary_data():
    """Load historical trends FY19-FY29"""
    file_path = DATA_DIR / 'Updated WW Long term financial planning FY19-FY25 - Summary.csv'
    df = pd.read_csv(file_path)

    years = ['FY19', 'FY20', 'FY21', 'FY22', 'FY23', 'FY24', 'FY25', 'FY26', 'FY27', 'FY28', 'FY29']

    # Income trends - columns 2-12 map to FY19-FY29
    income_trends = {
        'years': years,
        'program_revenue': [],
        'individual_donors': [],
        # ... other categories
    }

    for col_idx in range(2, 13):  # FY19 is col 2, FY29 is col 12
        income_trends['program_revenue'].append(clean_currency(df.iloc[17, col_idx]))
        income_trends['individual_donors'].append(clean_currency(df.iloc[18, col_idx]))
        # ... continue for all categories

    return {
        'income_trends': income_trends,
        'expense_trends': expense_trends,
        'financial_health': financial_health
    }
```

#### 3.5 Sankey Diagram Data Calculation

```python
def calculate_sankey_data(annual_data):
    """Generate Sankey diagram flow data"""
    revenue = annual_data['revenue']

    labels = [
        'Contributions',      # Index 0
        'Grants',            # Index 1
        'Earned Revenue',    # Index 2
        'Events',            # Index 3
        'Sponsorships',      # Index 4
        'Other',             # Index 5
        'Organization',      # Index 6 (central node)
        'Payroll',          # Index 7
        'Operations'        # Index 8
    ]

    # Revenue sources → Organization
    sources = [0, 1, 2, 3, 4, 5]
    targets = [6, 6, 6, 6, 6, 6]
    values = [
        revenue['contributions']['actual'],
        revenue['grants']['actual'],
        # ... all revenue values
    ]

    # Organization → Expenses
    payroll_total = (expenses['salaries_wages']['actual'] +
                     expenses['payroll_taxes']['actual'] +
                     expenses['benefits']['actual'])
    operations_total = expenses['total']['actual'] - payroll_total

    sources.extend([6, 6])
    targets.extend([7, 8])
    values.extend([payroll_total, operations_total])

    return {'labels': labels, 'sources': sources, 'targets': targets, 'values': values}
```

#### 3.6 Output Generation

```python
def main():
    """Main processing function"""
    print("Starting data processing...")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load all data
    summary_data = load_summary_data()
    annual_data = load_fy26_annual_data()
    program_data = load_program_data()
    cashflow_data = load_monthly_cashflow()
    sankey_data = calculate_sankey_data(annual_data)

    # Calculate executive summary
    executive_summary = {
        'current_reserves': annual_data['reserves']['current_reserves'],
        'months_in_reserve': annual_data['reserves']['months_reserve'],
        'reserve_health': 'good' if months >= 3 else 'warning' if months >= 2 else 'critical',
        'ytd_revenue': annual_data['revenue']['total']['actual'],
        'ytd_revenue_variance': safe_divide(...),
        # ... all KPI metrics
    }

    # Save JSON files
    with open(OUTPUT_DIR / 'executive_summary.json', 'w') as f:
        json.dump(executive_summary, f, indent=2)

    # ... save all other JSON files

    print("✅ Data processing complete!")
```

**Expected Output Files**:
- `executive_summary.json` (~400 bytes)
- `historical_trends.json` (~3KB)
- `revenue_data.json` (~900 bytes)
- `expense_data.json` (~500 bytes)
- `program_data.json` (~600 bytes)
- `cashflow_data.json` (~3KB)
- `sankey_data.json` (~450 bytes)

---

## React Application Components

### Step 4: Create React Entry Points

#### 4.1 `src/main.jsx`

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './App.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

**Purpose**: Bootstrap React app, mount to DOM

#### 4.2 `src/App.jsx`

```jsx
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom'
import ExecutiveSummary from './pages/ExecutiveSummary'
import RevenuePage from './pages/RevenuePage'
import ExpensePage from './pages/ExpensePage'
import CashFlowPage from './pages/CashFlowPage'
import ProgramsPage from './pages/ProgramsPage'
import './App.css'

function App() {
  return (
    <Router basename="/cohouser">  {/* CRITICAL: Must match vite.config.js */}
      <div className="app">
        <header className="header">
          <div className="header-content">
            <div>
              <h1>Wild Whatcom Financial Dashboard</h1>
              <p>FY26 Financial Health & Performance Tracker</p>
            </div>
          </div>
        </header>

        <nav className="nav">
          <div className="nav-content">
            <ul className="nav-links">
              <li><NavLink to="/" className="nav-link" end>📊 Executive Summary</NavLink></li>
              <li><NavLink to="/revenue" className="nav-link">💰 Revenue Analysis</NavLink></li>
              <li><NavLink to="/expenses" className="nav-link">📉 Expense Analysis</NavLink></li>
              <li><NavLink to="/cashflow" className="nav-link">🔄 Cash Flow & Reserves</NavLink></li>
              <li><NavLink to="/programs" className="nav-link">🎯 Programs & Planning</NavLink></li>
            </ul>
          </div>
        </nav>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<ExecutiveSummary />} />
            <Route path="/revenue" element={<RevenuePage />} />
            <Route path="/expenses" element={<ExpensePage />} />
            <Route path="/cashflow" element={<CashFlowPage />} />
            <Route path="/programs" element={<ProgramsPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
```

**Key Features**:
- `basename="/cohouser"` matches GitHub Pages path
- `NavLink` provides active state styling
- Emoji icons for visual navigation
- Sticky header and nav for easy navigation

### Step 5: Create Reusable Components

#### 5.1 `src/components/KPICard.jsx`

```jsx
import React from 'react'

export default function KPICard({ label, value, change, changeLabel, format = 'currency', health }) {
  const formatValue = (val) => {
    if (format === 'currency') {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 0,
      }).format(val)
    } else if (format === 'percent') {
      return `${val.toFixed(1)}%`
    } else if (format === 'number') {
      return val.toFixed(1)
    }
    return val
  }

  const getChangeClass = () => {
    if (change > 0) return 'positive'
    if (change < 0) return 'negative'
    return 'neutral'
  }

  const getChangeSymbol = () => {
    if (change > 0) return '▲'
    if (change < 0) return '▼'
    return '●'
  }

  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{formatValue(value)}</div>
      {change !== undefined && (
        <div className={`kpi-change ${getChangeClass()}`}>
          <span>{getChangeSymbol()}</span>
          <span>{formatValue(Math.abs(change))}</span>
          {changeLabel && <span className="text-secondary"> {changeLabel}</span>}
        </div>
      )}
      {health && (
        <div className="mt-2">
          <span className={`health-indicator ${health}`}>
            <span className="health-dot"></span>
            {health.charAt(0).toUpperCase() + health.slice(1)}
          </span>
        </div>
      )}
    </div>
  )
}
```

**Features**:
- Automatic number formatting (currency, percent, number)
- Color-coded change indicators (▲ green, ▼ red, ● neutral)
- Optional health badge (good/warning/critical)
- Flexible props for different use cases

#### 5.2 `src/components/SankeyChart.jsx`

```jsx
import React from 'react'
import Plot from 'react-plotly.js'

export default function SankeyChart({ data }) {
  if (!data) {
    return <div className="loading">Loading Sankey diagram...</div>
  }

  const trace = {
    type: 'sankey',
    orientation: 'h',
    node: {
      pad: 15,
      thickness: 20,
      line: { color: 'white', width: 1 },
      label: data.labels,
      color: [
        '#10b981', // Contributions - green
        '#3b82f6', // Grants - blue
        '#8b5cf6', // Earned Revenue - purple
        '#f59e0b', // Events - orange
        '#ec4899', // Sponsorships - pink
        '#6366f1', // Other - indigo
        '#2c5f2d', // Organization - dark green (Wild Whatcom brand)
        '#ef4444', // Payroll - red
        '#f97316', // Operations - orange
      ]
    },
    link: {
      source: data.sources,
      target: data.targets,
      value: data.values,
      color: 'rgba(0,0,0,0.2)'
    }
  }

  const layout = {
    title: { text: 'Revenue & Expense Flow', font: { size: 20, family: 'inherit' } },
    font: { size: 12, family: 'inherit' },
    height: 600,
    margin: { l: 20, r: 20, t: 60, b: 20 },
  }

  return (
    <div className="chart-container">
      <Plot
        data={[trace]}
        layout={layout}
        config={{ responsive: true, displayModeBar: false }}
        style={{ width: '100%' }}
      />
    </div>
  )
}
```

**Color Scheme**:
- Revenue sources: Varied colors for easy distinction
- Organization node: Wild Whatcom green (#2c5f2d)
- Payroll: Red (major expense)
- Operations: Orange (other expenses)

### Step 6: Create Dashboard Pages

#### 6.1 Page Structure Pattern

All pages follow this pattern:

```jsx
import React, { useState, useEffect } from 'react'
import Plot from 'react-plotly.js'

export default function PageName() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [data, setData] = useState({ /* initial state */ })

  useEffect(() => {
    const loadData = async () => {
      try {
        // Fetch multiple JSON files in parallel
        const [file1Res, file2Res] = await Promise.all([
          fetch('/cohouser/data/file1.json'),  // Note: includes basename
          fetch('/cohouser/data/file2.json'),
        ])

        const file1 = await file1Res.json()
        const file2 = await file2Res.json()

        setData({ file1, file2 })
        setLoading(false)
      } catch (err) {
        setError(err.message)
        setLoading(false)
      }
    }

    loadData()
  }, [])

  if (loading) return <div className="loading">Loading...</div>
  if (error) return <div className="error">Error: {error}</div>

  return (
    <div>
      {/* Page content */}
    </div>
  )
}
```

**Key Points**:
- Fetch paths include `/cohouser/` basename
- `Promise.all()` for parallel loading (faster)
- Loading and error states for UX
- `useEffect` with empty deps `[]` loads once on mount

#### 6.2 Executive Summary Page Structure

```jsx
// src/pages/ExecutiveSummary.jsx
- KPI Cards (4): Reserves, Revenue, Expenses, Net Income
- Reserve Progress Bar (3 targets: 1, 3, 6 months)
- Sankey Diagram (revenue flow)
- Revenue Trends Chart (line chart, FY19-FY26)
- Expense Trends Chart (line chart, FY19-FY26)
- Net Income Bar Chart (color-coded: green=positive, red=negative)
```

#### 6.3 Revenue Page Structure

```jsx
// src/pages/RevenuePage.jsx
- Total Revenue Summary Card
- Revenue Composition Pie Chart
- Budget vs Actual Bar Chart (grouped bars)
- Detailed Performance Table (with variance %)
- Multi-Year Trends Line Chart
```

#### 6.4 Expense Page Structure

```jsx
// src/pages/ExpensePage.jsx
- Total Expense Summary Card
- Payroll vs Operations Pie Chart
- Payroll Budget Tracking Bar Chart
- Detailed Expense Table
- Historical Stacked Area Chart
```

#### 6.5 Cash Flow Page Structure

```jsx
// src/pages/CashFlowPage.jsx
- Reserve KPI Cards (4)
- Reserve Progress Bars (3 levels with targets)
- Monthly Revenue/Expense Bar Chart
- Net Income Bar Chart
- Reserves Over Time Line Chart (dual-axis)
- Multi-Year Reserve Health Trend
```

#### 6.6 Programs Page Structure

```jsx
// src/pages/ProgramsPage.jsx
- Program Summary KPI Cards (3)
- Individual Program Performance Cards (5 programs)
- Budget vs Actual Bar Chart
- Financial Assistance Pie Chart
- Long-term Projections Line Chart
- Net Income Projections Bar Chart
- Strategic Insights Cards
```

---

## Styling & Design System

### Step 7: Create Global Styles

File: `src/App.css`

#### 7.1 CSS Variables (Design Tokens)

```css
:root {
  /* Colors - Wild Whatcom brand */
  --primary-color: #2c5f2d;      /* Wild Whatcom green */
  --secondary-color: #97bc62;     /* Light green */
  --accent-color: #00a9ce;        /* Blue */

  /* Semantic colors */
  --success-color: #10b981;       /* Green - positive */
  --warning-color: #f59e0b;       /* Orange - warning */
  --danger-color: #ef4444;        /* Red - critical */

  /* Neutral colors */
  --bg-color: #f8fafc;            /* Light gray background */
  --card-bg: #ffffff;             /* White cards */
  --text-primary: #1e293b;        /* Dark text */
  --text-secondary: #64748b;      /* Gray text */
  --border-color: #e2e8f0;        /* Light borders */

  /* Shadows */
  --shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
}
```

**Why CSS Variables?**:
- Easy theming (change once, applies everywhere)
- Consistent colors across dashboard
- Can be overridden for dark mode (future enhancement)

#### 7.2 Component Classes

```css
/* KPI Cards */
.kpi-card {
  background: var(--card-bg);
  border-radius: 0.75rem;
  padding: 1.5rem;
  box-shadow: var(--shadow-md);
  transition: transform 0.2s, box-shadow 0.2s;
}

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

/* Health Indicators */
.health-indicator.good {
  background-color: rgba(16, 185, 129, 0.1);
  color: var(--success-color);
}

.health-indicator.warning {
  background-color: rgba(245, 158, 11, 0.1);
  color: var(--warning-color);
}

.health-indicator.critical {
  background-color: rgba(239, 68, 68, 0.1);
  color: var(--danger-color);
}

/* Progress Bars */
.progress-bar {
  height: 8px;
  background-color: var(--border-color);
  border-radius: 9999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
  transition: width 0.3s ease;
}
```

#### 7.3 Responsive Design

```css
@media (max-width: 768px) {
  .kpi-grid {
    grid-template-columns: 1fr;  /* Stack on mobile */
  }

  .grid-2 {
    grid-template-columns: 1fr;  /* Stack charts on mobile */
  }

  .nav-links {
    overflow-x: auto;  /* Horizontal scroll on small screens */
  }
}
```

---

## Deployment Configuration

### Step 8: Create GitHub Actions Workflow

File: `.github/workflows/deploy.yml`

```yaml
name: Build and Deploy Dashboard

on:
  push:
    branches:
      - main
      - claude/*
  workflow_dispatch:  # Allow manual triggering

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      # Step 1: Get code
      - name: Checkout code
        uses: actions/checkout@v4

      # Step 2: Set up Python for data processing
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      # Step 3: Install Python dependencies
      - name: Install Python dependencies
        run: pip install pandas numpy

      # Step 4: Process CSV data → JSON
      - name: Process data
        run: python scripts/process_data.py
        working-directory: ./wild-whatcom-dashboard

      # Step 5: Set up Node.js
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: './wild-whatcom-dashboard/package-lock.json'

      # Step 6: Install Node dependencies
      - name: Install dependencies
        run: npm ci
        working-directory: ./wild-whatcom-dashboard

      # Step 7: Build React app
      - name: Build
        run: npm run build
        working-directory: ./wild-whatcom-dashboard

      # Step 8: Configure GitHub Pages
      - name: Setup Pages
        uses: actions/configure-pages@v4

      # Step 9: Upload build artifacts
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: './wild-whatcom-dashboard/dist'

      # Step 10: Deploy to GitHub Pages
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

**Workflow Explanation**:
1. **Trigger**: Runs on push to `main` or `claude/*` branches
2. **Python Setup**: Processes CSV files into JSON
3. **Node Setup**: Builds React app
4. **Deployment**: Publishes to GitHub Pages

**Critical Settings**:
- `working-directory: ./wild-whatcom-dashboard` - Assumes dashboard is in subfolder
- `cache: 'npm'` - Speeds up builds by caching dependencies
- `npm ci` instead of `npm install` - Uses lockfile, faster for CI

---

## Testing & Validation

### Step 9: Test Data Processing

```bash
# From project root
cd wild-whatcom-dashboard

# Run data processing
python scripts/process_data.py

# Expected output:
# Starting data processing...
# Loading summary data...
# Loading FY26 annual data...
# Loading program data...
# Loading monthly cash flow...
# Calculating Sankey diagram data...
# Calculating executive summary...
# Saving JSON files...
# ✅ Data processing complete! JSON files saved to .../public/data
```

**Verify JSON Files Created**:
```bash
ls -lh public/data/

# Should see:
# executive_summary.json (~400 bytes)
# historical_trends.json (~3KB)
# revenue_data.json (~900 bytes)
# expense_data.json (~500 bytes)
# program_data.json (~600 bytes)
# cashflow_data.json (~3KB)
# sankey_data.json (~450 bytes)
```

**Validate JSON Structure**:
```bash
# Check executive summary
cat public/data/executive_summary.json | python -m json.tool

# Should have keys:
# - current_reserves (number)
# - months_in_reserve (number)
# - reserve_health (string: "good"/"warning"/"critical")
# - ytd_revenue (number)
# - ytd_revenue_budget (number)
# - ytd_revenue_variance (number)
# - ytd_expenses (number)
# - ytd_expenses_budget (number)
# - ytd_expenses_variance (number)
# - net_income (number)
# - reserve_targets (object with one_month, three_months, six_months)
```

### Step 10: Test React Application Locally

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Expected output:
# VITE v5.1.0  ready in X ms
# ➜  Local:   http://localhost:5173/
# ➜  Network: use --host to expose
```

**Test Checklist**:
1. ✅ Navigate to http://localhost:5173
2. ✅ Check all 5 pages load without errors
3. ✅ Verify KPI cards show correct numbers
4. ✅ Test Sankey diagram renders
5. ✅ Hover over charts to see tooltips
6. ✅ Check mobile responsiveness (browser dev tools)
7. ✅ Verify navigation highlights active page
8. ✅ Check console for errors (F12 → Console tab)

### Step 11: Test Production Build

```bash
# Build for production
npm run build

# Expected output:
# vite v5.1.0 building for production...
# ✓ X modules transformed.
# dist/index.html                  X kB
# dist/assets/index-XXXXX.css      X kB
# dist/assets/index-XXXXX.js     XXX kB
# ✓ built in Xs

# Preview production build
npm run preview

# Navigate to http://localhost:4173
```

**Production Build Validation**:
1. ✅ All pages load correctly
2. ✅ Charts render properly
3. ✅ No console errors
4. ✅ Assets load (check Network tab)
5. ✅ Routing works (no 404s when refreshing pages)

---

## Verification Checklist

### ✅ Project Structure
- [ ] `wild-whatcom-dashboard/` directory exists
- [ ] All subdirectories created (`src/`, `public/`, `scripts/`, etc.)
- [ ] Configuration files present (package.json, vite.config.js, index.html)

### ✅ Data Processing
- [ ] `scripts/process_data.py` exists and is executable
- [ ] Helper functions handle edge cases (NaN, #REF!, division by zero)
- [ ] All 7 JSON files generated in `public/data/`
- [ ] JSON files contain valid data (no null/undefined values)
- [ ] File sizes are reasonable (~400B to ~3KB)

### ✅ React Components
- [ ] `src/main.jsx` bootstraps app correctly
- [ ] `src/App.jsx` includes router with correct basename
- [ ] `src/components/KPICard.jsx` formats numbers correctly
- [ ] `src/components/SankeyChart.jsx` renders Sankey diagram
- [ ] All 5 page components created

### ✅ Dashboard Pages
- [ ] **Executive Summary**: KPIs, Sankey, trends charts
- [ ] **Revenue Page**: Pie chart, bar chart, table, trends
- [ ] **Expense Page**: Pie chart, bar chart, table, stacked area
- [ ] **Cash Flow Page**: Monthly bars, net income, reserves over time
- [ ] **Programs Page**: Program cards, pie chart, projections

### ✅ Styling
- [ ] `src/App.css` defines CSS variables
- [ ] Wild Whatcom green (#2c5f2d) used as primary color
- [ ] Health indicators color-coded (green/orange/red)
- [ ] Responsive design works on mobile
- [ ] Hover effects on cards and charts

### ✅ GitHub Configuration
- [ ] `.gitignore` excludes `node_modules`, `dist`, `public/data/*.json`
- [ ] `.github/workflows/deploy.yml` workflow file created
- [ ] Workflow has correct permissions
- [ ] Working directory set to `./wild-whatcom-dashboard`

### ✅ Local Testing
- [ ] Data processing runs without errors
- [ ] `npm install` completes successfully
- [ ] `npm run dev` starts dev server
- [ ] All pages load in browser
- [ ] No console errors
- [ ] Charts render correctly
- [ ] Navigation works

### ✅ Production Build
- [ ] `npm run build` completes without errors
- [ ] `dist/` folder created with assets
- [ ] `npm run preview` serves production build
- [ ] Production build works identically to dev

### ✅ Deployment
- [ ] Code committed to git
- [ ] Pushed to GitHub repository
- [ ] GitHub Actions workflow runs successfully
- [ ] Deployed to GitHub Pages
- [ ] Live site accessible at https://[username].github.io/cohouser/

---

## Common Issues & Solutions

### Issue 1: JSON files not found (404 errors)

**Symptom**: Console shows "Failed to fetch /cohouser/data/executive_summary.json"

**Solutions**:
1. Check `public/data/` folder has JSON files
2. Run `python scripts/process_data.py` to generate files
3. Verify fetch paths include `/cohouser/` basename
4. Check `vite.config.js` has correct `base` setting

### Issue 2: Blank page / routing not working

**Symptom**: Homepage loads, but clicking nav links shows blank page

**Solutions**:
1. Check `basename="/cohouser"` in `App.jsx` Router
2. Verify it matches `base: '/cohouser/'` in `vite.config.js`
3. For local dev, might need `basename="/"` instead
4. Check browser console for errors

### Issue 3: Data processing fails with ValueError

**Symptom**: `ValueError: could not convert string to float: '#REF!'`

**Solutions**:
1. CSV files contain Excel errors - expected
2. Verify `clean_currency()` and `safe_float()` helper functions are present
3. Check functions handle `#REF!`, `#DIV/0!`, empty strings
4. Update CSV files to remove errors (or keep error handling)

### Issue 4: GitHub Actions workflow fails

**Symptom**: Workflow shows red X, deployment doesn't happen

**Solutions**:
1. Check "Actions" tab on GitHub for error logs
2. Verify `working-directory` is correct (./wild-whatcom-dashboard)
3. Ensure CSV data files are committed to repo
4. Check Python/Node versions match workflow file
5. Verify GitHub Pages is enabled in repo settings

### Issue 5: Charts don't render

**Symptom**: Blank spaces where charts should be

**Solutions**:
1. Check browser console for Plotly errors
2. Verify `react-plotly.js` and `plotly.js` are installed
3. Check JSON data is valid (not empty arrays)
4. Inspect element to see if chart div is present
5. Try different browser (clear cache)

---

## Performance Optimization Notes

### Data Processing
- **CSV to JSON conversion**: ~1-2 seconds for all files
- **JSON file sizes**: Total ~10KB (very small, fast loading)
- **Runs on every deployment**: Ensures data is always fresh

### React App
- **Initial load**: ~500KB total (React + Plotly.js)
- **Route-based code splitting**: Not implemented (all routes in one bundle)
- **Image optimization**: Not needed (no images except icons)
- **Plotly.js size**: ~3MB (largest dependency, but provides all chart functionality)

### Deployment
- **Build time**: ~30-60 seconds (depends on GitHub Actions runners)
- **Cache strategy**: npm dependencies cached, speeds up subsequent builds
- **CDN**: GitHub Pages serves via CDN, fast worldwide

---

## Future Enhancement Ideas

1. **PDF Export**: Add "Export to PDF" buttons using jsPDF
2. **Date Range Filtering**: Allow users to filter by fiscal year
3. **Scenario Planning**: Add "What-if" sliders for projections
4. **Real-time Updates**: WebSocket connection for live data updates
5. **Dark Mode**: Toggle between light/dark themes
6. **Comparison View**: Side-by-side comparison of multiple years
7. **Drill-down Modals**: Click chart segments to see detailed breakdowns
8. **Email Reports**: Schedule automated email summaries
9. **Mobile App**: React Native version for iOS/Android
10. **User Authentication**: Login for internal-only data

---

## Appendix A: File Size Reference

```
wild-whatcom-dashboard/
├── src/                           ~35KB (uncompressed)
│   ├── App.jsx                    2.5KB
│   ├── App.css                    7KB
│   ├── main.jsx                   0.3KB
│   ├── components/
│   │   ├── KPICard.jsx           1.5KB
│   │   └── SankeyChart.jsx       1.2KB
│   └── pages/
│       ├── ExecutiveSummary.jsx  6KB
│       ├── RevenuePage.jsx       7KB
│       ├── ExpensePage.jsx       6.5KB
│       ├── CashFlowPage.jsx      7.5KB
│       └── ProgramsPage.jsx      8KB
│
├── scripts/
│   └── process_data.py           15KB
│
├── public/data/                   ~10KB total
│
└── dist/ (after build)            ~3.5MB (includes Plotly.js)
```

---

## Appendix B: Color Palette Reference

| Color Name | Hex Code | Usage |
|------------|----------|-------|
| Wild Whatcom Green | `#2c5f2d` | Primary brand color, headers, organization node |
| Light Green | `#97bc62` | Secondary accent, gradients |
| Success Green | `#10b981` | Positive metrics, "good" health status |
| Warning Orange | `#f59e0b` | Warning metrics, "warning" health status |
| Danger Red | `#ef4444` | Critical metrics, negative variance |
| Blue | `#3b82f6` | Charts (grants, data series) |
| Purple | `#8b5cf6` | Charts (earned revenue) |
| Pink | `#ec4899` | Charts (sponsorships) |
| Indigo | `#6366f1` | Charts (other revenue) |

---

## Appendix C: Chart Types Used

| Chart Type | Library | Pages Used | Purpose |
|------------|---------|------------|---------|
| Sankey Diagram | Plotly.js | Executive Summary | Money flow visualization |
| Line Chart | Plotly.js | All pages | Trends over time |
| Bar Chart | Plotly.js | Revenue, Expense, Cash Flow | Budget vs actual, monthly data |
| Pie Chart | Plotly.js | Revenue, Expense, Programs | Composition breakdown |
| Stacked Area | Plotly.js | Expense | Cumulative trends |
| Grouped Bar | Plotly.js | Revenue, Programs | Category comparisons |

---

## Implementation Timeline Estimate

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Setup | Project structure, configs | 30 minutes |
| Data Processing | Python script, CSV parsing | 2 hours |
| React Components | KPI cards, Sankey chart | 1 hour |
| Dashboard Pages | 5 pages with charts | 4 hours |
| Styling | CSS, responsive design | 2 hours |
| Testing | Local testing, bug fixes | 1.5 hours |
| Deployment | GitHub Actions, Pages setup | 1 hour |
| **Total** | | **~12 hours** |

**Actual Time Taken**: Approximately 2-3 hours (with automation and AI assistance)

---

## Conclusion

This implementation plan provides a complete blueprint for recreating the Wild Whatcom Financial Dashboard. The architecture prioritizes:

1. **Simplicity**: Static site, no backend, minimal dependencies
2. **Maintainability**: Clear separation of concerns, reusable components
3. **Performance**: Pre-processed data, efficient rendering
4. **User Experience**: Interactive charts, responsive design, clear navigation
5. **Developer Experience**: Fast dev server, automated deployment, good documentation

Any developer following this plan should be able to:
- Understand the architectural decisions
- Recreate the dashboard from scratch
- Modify and extend the functionality
- Debug issues using the troubleshooting guide
- Deploy successfully to GitHub Pages

---

**Document Version**: 1.0
**Last Updated**: 2025-11-24
**Author**: Claude (Anthropic)
**Project**: Wild Whatcom Financial Dashboard
