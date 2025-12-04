# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CoHouser is a static HTML/JavaScript web application providing financial and utility analytics dashboards for the Bellingham Co-Housing Association (BCCA). It visualizes budget comparisons (2025 Approved vs 2026 Proposed) and water/sewer utility costs.

## Running the Application

No build step required - this is a static website.

```bash
# Option 1: Open HTML files directly in browser
open index.html

# Option 2: Serve with Python HTTP server
python3 -m http.server 8000
# Visit http://localhost:8000/index.html
```

## Technology Stack

- **Frontend**: HTML5, Vanilla JavaScript, CSS3
- **UI Framework**: Bootstrap 5.3.0
- **Charts**: Plotly.js v2.27.0, Chart.js
- **Data**: JSON objects embedded directly in HTML files
- **CDN**: All libraries loaded from jsDelivr/Plotly CDN (no local dependencies)

## Architecture

Each HTML file is a self-contained single-page dashboard:

| File | Purpose |
|------|---------|
| `index.html` | Landing portal with links to dashboards |
| `budget_analysis.html` | 2025 vs 2026 budget comparison with Sankey diagrams |
| `water_analysis.html` | 12-month water/sewer billing with consumption trends |
| `BCCAFinance.html` | Comprehensive finance dashboard (alternative view) |

**Data Flow**: PDF source documents (in `/data/`) → Manual extraction → JavaScript objects in HTML → Rendered charts

**Key Patterns**:
- Tab-based navigation for multi-period comparisons
- View mode toggle (currency $ vs percentage %)
- Responsive Bootstrap grid layout
- No build tools, no backend, no package installation required

## Data Sources

Source PDFs are stored in `/data/` but ignored by git:
- `2026 BCCA Budget First Read.pdf` - Budget source document
- `water_bill/` - Monthly water bills (Nov 2024 - Oct 2025)
