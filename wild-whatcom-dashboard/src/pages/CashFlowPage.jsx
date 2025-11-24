import React, { useState, useEffect } from 'react'
import Plot from 'react-plotly.js'

export default function CashFlowPage() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [data, setData] = useState({
    cashflow: null,
    executive: null,
    trends: null,
  })

  useEffect(() => {
    const loadData = async () => {
      try {
        const [cashflowRes, executiveRes, trendsRes] = await Promise.all([
          fetch('/cohouser/data/cashflow_data.json'),
          fetch('/cohouser/data/executive_summary.json'),
          fetch('/cohouser/data/historical_trends.json'),
        ])

        const cashflow = await cashflowRes.json()
        const executive = await executiveRes.json()
        const trends = await trendsRes.json()

        setData({ cashflow, executive, trends })
        setLoading(false)
      } catch (err) {
        setError(err.message)
        setLoading(false)
      }
    }

    loadData()
  }, [])

  if (loading) {
    return <div className="loading">Loading cash flow data...</div>
  }

  if (error) {
    return <div className="error">Error loading data: {error}</div>
  }

  const { cashflow, executive, trends } = data

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(value)
  }

  return (
    <div>
      <div className="mb-4">
        <h2 style={{ fontSize: '1.875rem', fontWeight: '700', marginBottom: '0.5rem' }}>
          Cash Flow & Reserves
        </h2>
        <p style={{ color: 'var(--text-secondary)' }}>
          Monthly cash flow tracking and reserve health monitoring
        </p>
      </div>

      {/* Reserve Status Cards */}
      <div className="kpi-grid mb-4">
        <div className="kpi-card">
          <div className="kpi-label">Current Reserves</div>
          <div className="kpi-value">{formatCurrency(executive.current_reserves)}</div>
          <div className={`health-indicator ${executive.reserve_health} mt-2`}>
            <span className="health-dot"></span>
            {executive.reserve_health.charAt(0).toUpperCase() + executive.reserve_health.slice(1)} Health
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Months in Reserve</div>
          <div className="kpi-value">{executive.months_in_reserve.toFixed(1)}</div>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Target: 3+ months
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">1 Month Target</div>
          <div className="kpi-value">{formatCurrency(executive.reserve_targets.one_month)}</div>
          <div style={{ fontSize: '0.875rem', color: executive.current_reserves >= executive.reserve_targets.one_month ? 'var(--success-color)' : 'var(--danger-color)', marginTop: '0.5rem' }}>
            {executive.current_reserves >= executive.reserve_targets.one_month ? '✓ Met' : '✗ Below target'}
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">3 Month Target</div>
          <div className="kpi-value">{formatCurrency(executive.reserve_targets.three_months)}</div>
          <div style={{ fontSize: '0.875rem', color: executive.current_reserves >= executive.reserve_targets.three_months ? 'var(--success-color)' : 'var(--warning-color)', marginTop: '0.5rem' }}>
            {executive.current_reserves >= executive.reserve_targets.three_months ? '✓ Met' : '○ In progress'}
          </div>
        </div>
      </div>

      {/* Reserve Progress Bar */}
      <div className="card mb-4">
        <div className="card-header">
          <h3 className="card-title">Reserve Targets</h3>
          <p className="card-subtitle">Progress toward reserve goals</p>
        </div>
        <div style={{ display: 'grid', gap: '1.5rem' }}>
          {/* 1 Month */}
          <div>
            <div className="progress-label">
              <span>1 Month Operating Expenses</span>
              <span>{((executive.current_reserves / executive.reserve_targets.one_month) * 100).toFixed(0)}%</span>
            </div>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{
                  width: `${Math.min((executive.current_reserves / executive.reserve_targets.one_month) * 100, 100)}%`,
                  background: executive.current_reserves >= executive.reserve_targets.one_month ? 'linear-gradient(90deg, #10b981, #059669)' : 'linear-gradient(90deg, #f59e0b, #d97706)'
                }}
              ></div>
            </div>
          </div>

          {/* 3 Months */}
          <div>
            <div className="progress-label">
              <span>3 Months Operating Expenses (Target)</span>
              <span>{((executive.current_reserves / executive.reserve_targets.three_months) * 100).toFixed(0)}%</span>
            </div>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{
                  width: `${Math.min((executive.current_reserves / executive.reserve_targets.three_months) * 100, 100)}%`,
                  background: executive.current_reserves >= executive.reserve_targets.three_months ? 'linear-gradient(90deg, #10b981, #059669)' : 'linear-gradient(90deg, #f59e0b, #d97706)'
                }}
              ></div>
            </div>
          </div>

          {/* 6 Months */}
          <div>
            <div className="progress-label">
              <span>6 Months Operating Expenses (Stretch Goal)</span>
              <span>{((executive.current_reserves / executive.reserve_targets.six_months) * 100).toFixed(0)}%</span>
            </div>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{
                  width: `${Math.min((executive.current_reserves / executive.reserve_targets.six_months) * 100, 100)}%`
                }}
              ></div>
            </div>
          </div>
        </div>
      </div>

      {/* Monthly Cash Flow */}
      <div className="card mb-4">
        <div className="card-header">
          <h3 className="card-title">Monthly Revenue & Expenses</h3>
          <p className="card-subtitle">FY26 monthly performance</p>
        </div>
        <Plot
          data={[
            {
              x: cashflow.revenue_by_month.months,
              y: cashflow.revenue_by_month.total,
              name: 'Revenue',
              type: 'bar',
              marker: { color: '#10b981' },
            },
            {
              x: cashflow.expense_by_month.months,
              y: cashflow.expense_by_month.total,
              name: 'Expenses',
              type: 'bar',
              marker: { color: '#ef4444' },
            },
          ]}
          layout={{
            height: 400,
            margin: { l: 60, r: 20, t: 20, b: 40 },
            xaxis: { title: '' },
            yaxis: { title: 'Amount ($)', tickformat: '$,.0f' },
            barmode: 'group',
            legend: { orientation: 'h', y: -0.15 },
            font: { family: 'inherit' },
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: '100%' }}
        />
      </div>

      {/* Net Income by Month */}
      <div className="card mb-4">
        <div className="card-header">
          <h3 className="card-title">Monthly Net Income</h3>
          <p className="card-subtitle">Monthly surplus/deficit</p>
        </div>
        <Plot
          data={[
            {
              x: cashflow.net_income_by_month.months,
              y: cashflow.net_income_by_month.net_income,
              type: 'bar',
              marker: {
                color: cashflow.net_income_by_month.net_income.map(v => v >= 0 ? '#10b981' : '#ef4444')
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
                x0: -0.5,
                x1: 11.5,
                y0: 0,
                y1: 0,
                line: { color: 'black', width: 2, dash: 'dash' }
              }
            ],
            showlegend: false,
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: '100%' }}
        />
      </div>

      {/* Reserves Over Time */}
      <div className="card mb-4">
        <div className="card-header">
          <h3 className="card-title">Reserve Balance Over Time</h3>
          <p className="card-subtitle">Monthly reserve tracking with months in reserve</p>
        </div>
        <Plot
          data={[
            {
              x: cashflow.net_income_by_month.months,
              y: cashflow.net_income_by_month.reserves,
              name: 'Reserve Balance',
              type: 'scatter',
              mode: 'lines+markers',
              line: { color: '#2c5f2d', width: 3 },
              marker: { size: 8 },
              yaxis: 'y',
            },
            {
              x: cashflow.net_income_by_month.months,
              y: cashflow.net_income_by_month.months_in_reserve,
              name: 'Months in Reserve',
              type: 'scatter',
              mode: 'lines+markers',
              line: { color: '#3b82f6', width: 3, dash: 'dot' },
              marker: { size: 8 },
              yaxis: 'y2',
            },
          ]}
          layout={{
            height: 400,
            margin: { l: 60, r: 60, t: 20, b: 40 },
            xaxis: { title: '' },
            yaxis: {
              title: 'Reserve Balance ($)',
              tickformat: '$,.0f',
              side: 'left',
            },
            yaxis2: {
              title: 'Months in Reserve',
              overlaying: 'y',
              side: 'right',
              showgrid: false,
            },
            legend: { orientation: 'h', y: -0.15 },
            font: { family: 'inherit' },
            hovermode: 'x unified',
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: '100%' }}
        />
      </div>

      {/* Historical Reserves Trend */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Multi-Year Reserve Health</h3>
          <p className="card-subtitle">Months in reserve trend (FY19-FY26)</p>
        </div>
        <Plot
          data={[
            {
              x: trends.financial_health.years,
              y: trends.financial_health.months_in_reserve,
              type: 'scatter',
              mode: 'lines+markers',
              line: { color: '#2c5f2d', width: 3 },
              marker: { size: 10 },
              fill: 'tozeroy',
              fillcolor: 'rgba(44, 95, 45, 0.2)',
            },
          ]}
          layout={{
            height: 400,
            margin: { l: 60, r: 20, t: 20, b: 40 },
            xaxis: { title: '' },
            yaxis: { title: 'Months in Reserve' },
            font: { family: 'inherit' },
            shapes: [
              {
                type: 'line',
                x0: trends.financial_health.years[0],
                x1: trends.financial_health.years[trends.financial_health.years.length - 1],
                y0: 3,
                y1: 3,
                line: { color: '#10b981', width: 2, dash: 'dash' },
              },
              {
                type: 'line',
                x0: trends.financial_health.years[0],
                x1: trends.financial_health.years[trends.financial_health.years.length - 1],
                y0: 2,
                y1: 2,
                line: { color: '#f59e0b', width: 2, dash: 'dash' },
              },
            ],
            annotations: [
              {
                x: trends.financial_health.years[trends.financial_health.years.length - 1],
                y: 3,
                xanchor: 'left',
                text: '  Target: 3 months',
                showarrow: false,
                font: { color: '#10b981', size: 12 },
              },
              {
                x: trends.financial_health.years[trends.financial_health.years.length - 1],
                y: 2,
                xanchor: 'left',
                text: '  Minimum: 2 months',
                showarrow: false,
                font: { color: '#f59e0b', size: 12 },
              },
            ],
            showlegend: false,
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: '100%' }}
        />
      </div>
    </div>
  )
}
