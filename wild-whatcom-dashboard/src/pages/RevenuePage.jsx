import React, { useState, useEffect } from 'react'
import Plot from 'react-plotly.js'

export default function RevenuePage() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [data, setData] = useState({
    revenue: null,
    trends: null,
  })

  useEffect(() => {
    const loadData = async () => {
      try {
        const [revenueRes, trendsRes] = await Promise.all([
          fetch('/cohouser/data/revenue_data.json'),
          fetch('/cohouser/data/historical_trends.json'),
        ])

        const revenue = await revenueRes.json()
        const trends = await trendsRes.json()

        setData({ revenue, trends })
        setLoading(false)
      } catch (err) {
        setError(err.message)
        setLoading(false)
      }
    }

    loadData()
  }, [])

  if (loading) {
    return <div className="loading">Loading revenue data...</div>
  }

  if (error) {
    return <div className="error">Error loading data: {error}</div>
  }

  const { revenue, trends } = data

  // Calculate variance percentages
  const calculateVariance = (actual, budgeted) => {
    return ((actual - budgeted) / budgeted) * 100
  }

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(value)
  }

  // Prepare budget vs actual data
  const categories = ['Contributions', 'Grants', 'Earned Revenue', 'Events', 'Sponsorships', 'Other']
  const budgetedValues = [
    revenue.contributions.budgeted,
    revenue.grants.budgeted,
    revenue.earned_revenue.budgeted,
    revenue.fundraising_events.budgeted,
    revenue.sponsorships.budgeted,
    revenue.other.budgeted,
  ]
  const actualValues = [
    revenue.contributions.actual,
    revenue.grants.actual,
    revenue.earned_revenue.actual,
    revenue.fundraising_events.actual,
    revenue.sponsorships.actual,
    revenue.other.actual,
  ]

  // Prepare pie chart data
  const pieData = {
    labels: categories,
    values: actualValues,
    colors: ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ec4899', '#6366f1']
  }

  return (
    <div>
      <div className="mb-4">
        <h2 style={{ fontSize: '1.875rem', fontWeight: '700', marginBottom: '0.5rem' }}>
          Revenue Deep Dive
        </h2>
        <p style={{ color: 'var(--text-secondary)' }}>
          Comprehensive analysis of all revenue streams for FY26
        </p>
      </div>

      {/* Total Revenue Summary */}
      <div className="card mb-4">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
              TOTAL REVENUE (YTD)
            </div>
            <div style={{ fontSize: '2.5rem', fontWeight: '700' }}>
              {formatCurrency(revenue.total.actual)}
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
              BUDGET
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--text-secondary)' }}>
              {formatCurrency(revenue.total.budgeted)}
            </div>
            <div style={{ fontSize: '0.875rem', color: calculateVariance(revenue.total.actual, revenue.total.budgeted) >= 0 ? 'var(--success-color)' : 'var(--danger-color)', marginTop: '0.5rem' }}>
              {calculateVariance(revenue.total.actual, revenue.total.budgeted) >= 0 ? '▲' : '▼'} {Math.abs(calculateVariance(revenue.total.actual, revenue.total.budgeted)).toFixed(1)}% vs budget
            </div>
          </div>
        </div>
      </div>

      {/* Revenue Composition */}
      <div className="grid-2 mb-4">
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Revenue Composition</h3>
            <p className="card-subtitle">FY26 Actual revenue by source</p>
          </div>
          <Plot
            data={[
              {
                type: 'pie',
                labels: pieData.labels,
                values: pieData.values,
                marker: {
                  colors: pieData.colors
                },
                textinfo: 'label+percent',
                textposition: 'auto',
                hovertemplate: '<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>',
              }
            ]}
            layout={{
              height: 400,
              margin: { l: 20, r: 20, t: 20, b: 20 },
              font: { family: 'inherit' },
              showlegend: false,
            }}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%' }}
          />
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Budget vs Actual</h3>
            <p className="card-subtitle">FY26 performance by revenue category</p>
          </div>
          <Plot
            data={[
              {
                x: categories,
                y: budgetedValues,
                name: 'Budgeted',
                type: 'bar',
                marker: { color: 'rgba(100, 116, 139, 0.5)' },
              },
              {
                x: categories,
                y: actualValues,
                name: 'Actual',
                type: 'bar',
                marker: { color: '#2c5f2d' },
              },
            ]}
            layout={{
              height: 400,
              margin: { l: 60, r: 20, t: 20, b: 80 },
              xaxis: { tickangle: -45 },
              yaxis: { title: 'Amount ($)', tickformat: '$,.0f' },
              barmode: 'group',
              legend: { orientation: 'h', y: -0.3 },
              font: { family: 'inherit' },
            }}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%' }}
          />
        </div>
      </div>

      {/* Detailed Category Performance */}
      <div className="card mb-4">
        <div className="card-header">
          <h3 className="card-title">Category Performance</h3>
          <p className="card-subtitle">Detailed breakdown with variance analysis</p>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border-color)', textAlign: 'left' }}>
                <th style={{ padding: '0.75rem', fontWeight: '600' }}>Category</th>
                <th style={{ padding: '0.75rem', fontWeight: '600', textAlign: 'right' }}>Budgeted</th>
                <th style={{ padding: '0.75rem', fontWeight: '600', textAlign: 'right' }}>Actual</th>
                <th style={{ padding: '0.75rem', fontWeight: '600', textAlign: 'right' }}>Variance</th>
                <th style={{ padding: '0.75rem', fontWeight: '600', textAlign: 'right' }}>% of Total</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(revenue).filter(([key]) => key !== 'total').map(([key, values]) => {
                const variance = calculateVariance(values.actual, values.budgeted)
                const percentOfTotal = (values.actual / revenue.total.actual) * 100
                return (
                  <tr key={key} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '0.75rem', fontWeight: '500' }}>
                      {key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'right', color: 'var(--text-secondary)' }}>
                      {formatCurrency(values.budgeted)}
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'right', fontWeight: '600' }}>
                      {formatCurrency(values.actual)}
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'right', color: variance >= 0 ? 'var(--success-color)' : 'var(--danger-color)', fontWeight: '600' }}>
                      {variance >= 0 ? '+' : ''}{variance.toFixed(1)}%
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                      {percentOfTotal.toFixed(1)}%
                    </td>
                  </tr>
                )
              })}
              <tr style={{ borderTop: '2px solid var(--border-color)', fontWeight: '700' }}>
                <td style={{ padding: '0.75rem' }}>TOTAL</td>
                <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                  {formatCurrency(revenue.total.budgeted)}
                </td>
                <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                  {formatCurrency(revenue.total.actual)}
                </td>
                <td style={{ padding: '0.75rem', textAlign: 'right', color: calculateVariance(revenue.total.actual, revenue.total.budgeted) >= 0 ? 'var(--success-color)' : 'var(--danger-color)' }}>
                  {calculateVariance(revenue.total.actual, revenue.total.budgeted) >= 0 ? '+' : ''}{calculateVariance(revenue.total.actual, revenue.total.budgeted).toFixed(1)}%
                </td>
                <td style={{ padding: '0.75rem', textAlign: 'right' }}>100.0%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Multi-Year Trends */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Multi-Year Revenue Trends</h3>
          <p className="card-subtitle">Historical performance (FY19-FY26)</p>
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
              marker: { size: 8 },
            },
            {
              x: trends.income_trends.years,
              y: trends.income_trends.grants,
              name: 'Grants',
              type: 'scatter',
              mode: 'lines+markers',
              line: { color: '#3b82f6', width: 3 },
              marker: { size: 8 },
            },
            {
              x: trends.income_trends.years,
              y: trends.income_trends.individual_donors,
              name: 'Donations',
              type: 'scatter',
              mode: 'lines+markers',
              line: { color: '#10b981', width: 3 },
              marker: { size: 8 },
            },
            {
              x: trends.income_trends.years,
              y: trends.income_trends.business_sponsors,
              name: 'Sponsorships',
              type: 'scatter',
              mode: 'lines+markers',
              line: { color: '#ec4899', width: 3 },
              marker: { size: 8 },
            },
            {
              x: trends.income_trends.years,
              y: trends.income_trends.events,
              name: 'Events',
              type: 'scatter',
              mode: 'lines+markers',
              line: { color: '#f59e0b', width: 3 },
              marker: { size: 8 },
            },
          ]}
          layout={{
            height: 500,
            margin: { l: 60, r: 20, t: 20, b: 40 },
            xaxis: { title: '' },
            yaxis: { title: 'Amount ($)', tickformat: '$,.0f' },
            legend: { orientation: 'h', y: -0.15 },
            font: { family: 'inherit' },
            hovermode: 'x unified',
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: '100%' }}
        />
      </div>
    </div>
  )
}
