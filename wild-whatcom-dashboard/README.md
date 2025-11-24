# Wild Whatcom Financial Dashboard

A comprehensive, interactive financial dashboard for Wild Whatcom nonprofit organization, displaying financial health, revenue/expense tracking, cash flow, and program-level performance metrics.

## Features

### 📊 Executive Summary
- **Financial Health at a Glance**: Current reserves, months in reserve, year-to-date performance
- **Sankey Diagram**: Visual money flow from revenue sources through the organization to expenses
- **KPI Cards**: Real-time metrics with variance tracking vs budget
- **Reserve Health Tracking**: Progress bars showing current vs target reserves (1, 3, and 6 months)
- **Historical Trends**: Multi-year revenue, expense, and net income trends (FY19-FY26)

### 💰 Revenue Deep Dive
- Budget vs Actual comparison for all revenue categories
- Revenue composition pie chart
- Detailed variance analysis table
- Multi-year revenue trends by source
- Performance tracking: Contributions, Grants, Earned Revenue, Events, Sponsorships

### 📉 Expense Analysis
- Payroll vs Operating Expenses split
- Budget tracking for all expense categories
- Detailed breakdown with variance percentages
- Historical expense trends
- Cost efficiency metrics

### 🔄 Cash Flow & Reserves
- Monthly revenue and expense tracking
- Net income by month visualization
- Reserve balance over time with months-in-reserve overlay
- Multi-year reserve health trends
- Reserve target benchmarks (1, 3, 6 months)

### 🎯 Programs & Long-term Planning
- Individual program performance cards
- Budget vs Actual for each program
- Financial assistance (scholarships) by program
- Multi-year projections (FY19-FY29)
- Strategic financial insights

## Technology Stack

- **Frontend**: React 18 + Vite
- **Visualizations**: Plotly.js for interactive charts and Sankey diagrams
- **Routing**: React Router v6
- **Data Processing**: Python (Pandas, NumPy)
- **Deployment**: GitHub Pages (static site)
- **CI/CD**: GitHub Actions

## Project Structure

```
wild-whatcom-dashboard/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions workflow
├── public/
│   └── data/                   # Generated JSON files (git-ignored)
├── scripts/
│   └── process_data.py         # Data processing script
├── src/
│   ├── components/             # Reusable React components
│   │   ├── KPICard.jsx
│   │   └── SankeyChart.jsx
│   ├── pages/                  # Dashboard pages
│   │   ├── ExecutiveSummary.jsx
│   │   ├── RevenuePage.jsx
│   │   ├── ExpensePage.jsx
│   │   ├── CashFlowPage.jsx
│   │   └── ProgramsPage.jsx
│   ├── App.jsx                 # Main app component
│   ├── App.css                 # Global styles
│   └── main.jsx                # Entry point
├── index.html
├── package.json
├── vite.config.js
└── README.md
```

## Local Development

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- Git

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd wild-whatcom-dashboard
   ```

2. **Install Python dependencies**
   ```bash
   pip install pandas numpy
   ```

3. **Process the data** (generates JSON files from CSVs)
   ```bash
   python scripts/process_data.py
   ```

   This will create JSON files in `public/data/`:
   - `executive_summary.json`
   - `historical_trends.json`
   - `revenue_data.json`
   - `expense_data.json`
   - `program_data.json`
   - `cashflow_data.json`
   - `sankey_data.json`

4. **Install Node dependencies**
   ```bash
   npm install
   ```

5. **Start development server**
   ```bash
   npm run dev
   ```

6. **Open browser** to http://localhost:5173

### Building for Production

```bash
npm run build
```

The production build will be created in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Data Processing

The `scripts/process_data.py` script reads CSV files from `../data/wild_whatcom_finance/` and generates static JSON files for the dashboard.

### Key Data Sources (CSV Files)

- **Summary**: `Updated WW Long term financial planning FY19-FY25 - Summary.csv`
- **FY26 Budget**: `FY26 Budget - Approved 6_26_2025 - Budget as Passed - 6252025.csv`
- **FY26 Actuals**: `FY 26 Cash Flow Projections (budget+actuals) - Annual.csv`
- **Monthly Cash Flow**: `FY 26 Cash Flow Projections (budget+actuals) - R + E by monthyear.csv`
- **Program Data**: `FY 26 Cash Flow Projections (budget+actuals) - high level Income review.csv`

### Updating the Data

When you receive new CSV files:

1. Replace the CSV files in `../data/wild_whatcom_finance/`
2. Run the data processing script:
   ```bash
   python scripts/process_data.py
   ```
3. The dashboard will automatically use the updated JSON files

## Deployment

### GitHub Pages (Automatic)

The dashboard automatically deploys to GitHub Pages when you push to the `main` branch or any `claude/*` branch.

**GitHub Actions Workflow**:
1. Checks out code
2. Installs Python dependencies
3. Runs data processing script
4. Installs Node dependencies
5. Builds the React app
6. Deploys to GitHub Pages

**Access the live dashboard**: `https://<your-username>.github.io/cohouser/`

### Manual Deployment

If you need to deploy manually:

1. Process the data: `python scripts/process_data.py`
2. Build the app: `npm run build`
3. Deploy the `dist/` folder to your hosting provider

## Configuration

### Base URL

The app is configured for GitHub Pages deployment at `/cohouser/`. To change this:

1. Edit `vite.config.js`:
   ```js
   export default defineConfig({
     base: '/your-repo-name/',
     // ...
   })
   ```

2. Edit `src/App.jsx`:
   ```jsx
   <Router basename="/your-repo-name">
   ```

### Color Scheme

Colors are defined in `src/App.css` using CSS variables:

```css
:root {
  --primary-color: #2c5f2d;      /* Wild Whatcom green */
  --secondary-color: #97bc62;     /* Light green */
  --accent-color: #00a9ce;        /* Blue */
  --success-color: #10b981;       /* Green */
  --warning-color: #f59e0b;       /* Orange */
  --danger-color: #ef4444;        /* Red */
}
```

## Key Metrics & Calculations

### Financial Health Score
- **Good**: ≥ 3 months of operating reserves
- **Warning**: 2-3 months of reserves
- **Critical**: < 2 months of reserves

### Budget Variance
```
Variance % = ((Actual - Budget) / Budget) × 100
```

### Months in Reserve
```
Months in Reserve = Current Reserves / Monthly Operating Expenses
```

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Performance

- All data is pre-processed and served as static JSON
- No server-side processing required
- Fast, client-side rendering
- Optimized Plotly.js charts

## Troubleshooting

### Data not loading
- Check that JSON files exist in `public/data/`
- Run `python scripts/process_data.py` to regenerate
- Check browser console for errors

### Charts not rendering
- Ensure all required npm packages are installed: `npm install`
- Clear browser cache
- Check that JSON data is valid

### Build errors
- Delete `node_modules/` and run `npm install` again
- Delete `dist/` folder
- Ensure Node.js version is 18+

## Future Enhancements

- [ ] Export to PDF functionality
- [ ] Real-time CSV upload without re-deployment
- [ ] Custom date range filtering
- [ ] Scenario planning tools
- [ ] Email report scheduling
- [ ] Mobile app version

## License

Proprietary - Wild Whatcom

## Support

For questions or issues, contact the Wild Whatcom financial team.

---

**Built with ❤️ for Wild Whatcom**
