import React, { useState, useEffect } from 'react'
import KPICard from '../components/KPICard'
import SankeyChart from '../components/SankeyChart'
import Plot from 'react-plotly.js'

export default function ExecutiveSummary() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [data, setData] = useState({
    executive: null,
    sankey: null,
    trends: null,
  })

  useEffect(() => {
    const loadData = async () => {
      try {
        const [executiveRes, sankeyRes, trendsRes] = await Promise.all([
          fetch('/cohouser/data/executive_summary.json'),
          fetch('/cohouser/data/sankey_data.json'),
          fetch('/cohouser/data/historical_trends.json'),
        ])

        const executive = await executiveRes.json()
        const sankey = await sankeyRes.json()
        const trends = await trendsRes.json()

        setData({ executive, sankey, trends })
        setLoading(false)
      } catch (err) {
        setError(err.message)
        setLoading(false)
      }
    }

    loadData()
  }, [])

  if (loading) {
    return <div className="loading">Loading dashboard...</div>
  }

  if (error) {
    return <div className="error">Error loading data: {error}</div>
  }

  const { executive, sankey, trends } = data

  // Calculate reserve progress for visualization
  const reserveProgress = (executive.current_reserves / executive.reserve_targets.three_months) * 100

  return (
    <div>
      <div className="mb-4">
        <h2 style={{ fontSize: '1.875rem', fontWeight: '700', marginBottom: '0.5rem' }}>
          Financial Health at a Glance
        </h2>
        <p style={{ color: 'var(--text-secondary)' }}>
          Real-time snapshot of Wild Whatcom's financial position for FY26
        </p>
      </div>

      {/* KPI Cards */}
      <div className="kpi-grid">
        <KPICard
          label="Current Reserves"
          value={executive.current_reserves}
          change={executive.months_in_reserve}
          changeLabel="months"
          format="currency"
          health={executive.reserve_health}
        />
        <KPICard
          label="YTD Revenue"
          value={executive.ytd_revenue}
          change={executive.ytd_revenue_variance}
          changeLabel="vs budget"
          format="currency"
        />
        <KPICard
          label="YTD Expenses"
          value={executive.ytd_expenses}
          change={executive.ytd_expenses_variance}
          changeLabel="vs budget"
          format="currency"
        />
        <KPICard
          label="Net Income"
          value={executive.net_income}
          format="currency"
        />
      </div>

      {/* Reserve Progress */}
      <div className="card mb-4">
        <div className="card-header">
          <h3 className="card-title">Reserve Health</h3>
          <p className="card-subtitle">Current reserves vs target benchmarks</p>
        </div>
        <div className="progress-bar-container">
          <div className="progress-label">
            <span>
              Current: {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(executive.current_reserves)}
            </span>
            <span>
              Target (3 months): {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(executive.reserve_targets.three_months)}
            </span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${Math.min(reserveProgress, 100)}%` }}></div>
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1.5rem', fontSize: '0.875rem' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>
              {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(executive.reserve_targets.one_month)}
            </div>
            <div style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>1 Month</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>
              {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(executive.reserve_targets.three_months)}
            </div>
            <div style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>3 Months</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>
              {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(executive.reserve_targets.six_months)}
            </div>
            <div style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>6 Months</div>
          </div>
        </div>
      </div>

      {/* Sankey Diagram */}
      <div className="card mb-4">
        <div className="card-header">
          <h3 className="card-title">Money Flow Visualization</h3>
          <p className="card-subtitle">How revenue flows through the organization to expenses</p>
        </div>
        <SankeyChart data={sankey} />
      </div>

      {/* Historical Trends */}
      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Revenue Trends</h3>
            <p className="card-subtitle">Historical revenue by category (FY19-FY26)</p>
          </div>
          <Plot
            data={[
              {
                x: trends.income_trends.years,
                y: trends.income_trends.program_revenue,
                name: 'Program Revenue',
                type: 'scatter',
                mode: 'lines+markers',
                line: { color: '#8b5cf6', width: 3 },
              },
              {
                x: trends.income_trends.years,
                y: trends.income_trends.grants,
                name: 'Grants',
                type: 'scatter',
                mode: 'lines+markers',
                line: { color: '#3b82f6', width: 3 },
              },
              {
                x: trends.income_trends.years,
                y: trends.income_trends.individual_donors,
                name: 'Donations',
                type: 'scatter',
                mode: 'lines+markers',
                line: { color: '#10b981', width: 3 },
              },
            ]}
            layout={{
              height: 400,
              margin: { l: 60, r: 20, t: 20, b: 40 },
              xaxis: { title: '' },
              yaxis: { title: 'Amount ($)', tickformat: '$,.0f' },
              legend: { orientation: 'h', y: -0.2 },
              font: { family: 'inherit' },
            }}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%' }}
          />
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Expense Trends</h3>
            <p className="card-subtitle">Historical expenses by category (FY19-FY26)</p>
          </div>
          <Plot
            data={[
              {
                x: trends.expense_trends.years,
                y: trends.expense_trends.salaries_wages_benefits,
                name: 'Payroll & Benefits',
                type: 'scatter',
                mode: 'lines+markers',
                line: { color: '#ef4444', width: 3 },
              },
              {
                x: trends.expense_trends.years,
                y: trends.expense_trends.operating_expenses,
                name: 'Operating Expenses',
                type: 'scatter',
                mode: 'lines+markers',
                line: { color: '#f97316', width: 3 },
              },
            ]}
            layout={{
              height: 400,
              margin: { l: 60, r: 20, t: 20, b: 40 },
              xaxis: { title: '' },
              yaxis: { title: 'Amount ($)', tickformat: '$,.0f' },
              legend: { orientation: 'h', y: -0.2 },
              font: { family: 'inherit' },
            }}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%' }}
          />
        </div>
      </div>

      {/* Net Income Trend */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Net Income & Reserve Health</h3>
          <p className="card-subtitle">Historical net income and months in reserve (FY19-FY26)</p>
        </div>
        <Plot
          data={[
            {
              x: trends.financial_health.years,
              y: trends.financial_health.net_income,
              name: 'Net Income',
              type: 'bar',
              marker: {
                color: trends.financial_health.net_income.map(v => v >= 0 ? '#10b981' : '#ef4444')
              },
            },
          ]}
          layout={{
            height: 400,
            margin: { l: 60, r: 20, t: 20, b: 40 },
            xaxis: { title: '' },
            yaxis: { title: 'Net Income ($)', tickformat: '$,.0f' },
            font: { family: 'inherit' },
            shapes: [
              {
                type: 'line',
                x0: trends.financial_health.years[0],
                x1: trends.financial_health.years[trends.financial_health.years.length - 1],
                y0: 0,
                y1: 0,
                line: { color: 'black', width: 2, dash: 'dash' }
              }
            ]
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: '100%' }}
        />
      </div>
    </div>
  )
}
