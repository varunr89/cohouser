import React, { useState, useEffect } from 'react'
import Plot from 'react-plotly.js'

export default function ProgramsPage() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [data, setData] = useState({
    programs: null,
    trends: null,
  })

  useEffect(() => {
    const loadData = async () => {
      try {
        const [programsRes, trendsRes] = await Promise.all([
          fetch('/cohouser/data/program_data.json'),
          fetch('/cohouser/data/historical_trends.json'),
        ])

        const programs = await programsRes.json()
        const trends = await trendsRes.json()

        setData({ programs, trends })
        setLoading(false)
      } catch (err) {
        setError(err.message)
        setLoading(false)
      }
    }

    loadData()
  }, [])

  if (loading) {
    return <div className="loading">Loading program data...</div>
  }

  if (error) {
    return <div className="error">Error loading data: {error}</div>
  }

  const { programs, trends } = data

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(value)
  }

  // Calculate total scholarships
  const totalScholarships = Object.values(programs).reduce((sum, prog) => sum + (prog.scholarships || 0), 0)

  // Prepare program performance data
  const programNames = Object.keys(programs).map(key =>
    key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
  )
  const programActuals = Object.values(programs).map(p => p.actual || 0)
  const programBudgets = Object.values(programs).map(p => p.budgeted || 0)
  const programScholarships = Object.values(programs).map(p => p.scholarships || 0)

  return (
    <div>
      <div className="mb-4">
        <h2 style={{ fontSize: '1.875rem', fontWeight: '700', marginBottom: '0.5rem' }}>
          Programs & Long-term Planning
        </h2>
        <p style={{ color: 'var(--text-secondary)' }}>
          Program-level performance and strategic financial projections
        </p>
      </div>

      {/* Program Performance Summary */}
      <div className="kpi-grid mb-4">
        <div className="kpi-card">
          <div className="kpi-label">Total Program Revenue</div>
          <div className="kpi-value">
            {formatCurrency(programActuals.reduce((sum, val) => sum + val, 0))}
          </div>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Across {Object.keys(programs).length} programs
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Financial Assistance Provided</div>
          <div className="kpi-value">{formatCurrency(totalScholarships)}</div>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Scholarships & aid
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Average Goal Achievement</div>
          <div className="kpi-value">
            {(Object.values(programs)
              .filter(p => p.percent_of_goal)
              .reduce((sum, p) => sum + p.percent_of_goal, 0) /
              Object.values(programs).filter(p => p.percent_of_goal).length * 100).toFixed(1)}%
          </div>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Of budgeted revenue
          </div>
        </div>
      </div>

      {/* Program Performance Cards */}
      <div className="mb-4">
        <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem' }}>
          Individual Program Performance
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
          {Object.entries(programs).map(([key, program]) => {
            const percentOfGoal = program.percent_of_goal ? program.percent_of_goal * 100 : 0
            const variance = program.budgeted ? ((program.actual - program.budgeted) / program.budgeted * 100) : 0
            return (
              <div key={key} className="card">
                <div style={{ marginBottom: '1rem' }}>
                  <h4 style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '0.5rem' }}>
                    {key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
                  </h4>
                </div>
                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Actual</span>
                    <span style={{ fontSize: '0.875rem', fontWeight: '600' }}>{formatCurrency(program.actual || 0)}</span>
                  </div>
                  {program.budgeted && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Budget</span>
                      <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>{formatCurrency(program.budgeted)}</span>
                    </div>
                  )}
                  {program.scholarships > 0 && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Financial Aid</span>
                      <span style={{ fontSize: '0.875rem', color: 'var(--primary-color)', fontWeight: '600' }}>
                        {formatCurrency(program.scholarships)}
                      </span>
                    </div>
                  )}
                </div>
                {percentOfGoal > 0 && (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.5rem' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>Goal Achievement</span>
                      <span style={{ fontWeight: '600' }}>{percentOfGoal.toFixed(1)}%</span>
                    </div>
                    <div className="progress-bar">
                      <div
                        className="progress-fill"
                        style={{
                          width: `${Math.min(percentOfGoal, 100)}%`,
                          background: percentOfGoal >= 90 ? 'linear-gradient(90deg, #10b981, #059669)' :
                                      percentOfGoal >= 70 ? 'linear-gradient(90deg, #f59e0b, #d97706)' :
                                      'linear-gradient(90deg, #ef4444, #dc2626)'
                        }}
                      ></div>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Program Revenue Comparison */}
      <div className="card mb-4">
        <div className="card-header">
          <h3 className="card-title">Program Revenue: Budget vs Actual</h3>
          <p className="card-subtitle">FY26 performance by program</p>
        </div>
        <Plot
          data={[
            {
              x: programNames,
              y: programBudgets,
              name: 'Budgeted',
              type: 'bar',
              marker: { color: 'rgba(100, 116, 139, 0.5)' },
            },
            {
              x: programNames,
              y: programActuals,
              name: 'Actual',
              type: 'bar',
              marker: { color: '#2c5f2d' },
            },
          ]}
          layout={{
            height: 400,
            margin: { l: 60, r: 20, t: 20, b: 100 },
            xaxis: { tickangle: -45 },
            yaxis: { title: 'Revenue ($)', tickformat: '$,.0f' },
            barmode: 'group',
            legend: { orientation: 'h', y: -0.35 },
            font: { family: 'inherit' },
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: '100%' }}
        />
      </div>

      {/* Financial Assistance by Program */}
      <div className="card mb-4">
        <div className="card-header">
          <h3 className="card-title">Financial Assistance by Program</h3>
          <p className="card-subtitle">Scholarships and aid distribution</p>
        </div>
        <Plot
          data={[
            {
              type: 'pie',
              labels: programNames,
              values: programScholarships,
              marker: {
                colors: ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ec4899']
              },
              textinfo: 'label+value',
              texttemplate: '<b>%{label}</b><br>$%{value:,.0f}',
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

      {/* Long-term Financial Projections */}
      <div className="card mb-4">
        <div className="card-header">
          <h3 className="card-title">Long-term Financial Projections</h3>
          <p className="card-subtitle">Multi-year income and expense trends (FY19-FY29)</p>
        </div>
        <Plot
          data={[
            {
              x: trends.income_trends.years,
              y: trends.income_trends.total,
              name: 'Projected Income',
              type: 'scatter',
              mode: 'lines+markers',
              line: { color: '#10b981', width: 3 },
              marker: { size: 8 },
            },
            {
              x: trends.expense_trends.years,
              y: trends.expense_trends.total,
              name: 'Projected Expenses',
              type: 'scatter',
              mode: 'lines+markers',
              line: { color: '#ef4444', width: 3 },
              marker: { size: 8 },
            },
          ]}
          layout={{
            height: 500,
            margin: { l: 60, r: 20, t: 20, b: 40 },
            xaxis: {
              title: '',
              showgrid: true,
              gridcolor: 'rgba(0,0,0,0.1)',
            },
            yaxis: {
              title: 'Amount ($)',
              tickformat: '$,.0f',
              showgrid: true,
              gridcolor: 'rgba(0,0,0,0.1)',
            },
            legend: { orientation: 'h', y: -0.15 },
            font: { family: 'inherit' },
            hovermode: 'x unified',
            shapes: [
              {
                type: 'rect',
                xref: 'x',
                yref: 'paper',
                x0: 'FY26',
                x1: 'FY29',
                y0: 0,
                y1: 1,
                fillcolor: 'rgba(59, 130, 246, 0.1)',
                line: { width: 0 },
              }
            ],
            annotations: [
              {
                x: 'FY27',
                y: 1,
                yref: 'paper',
                text: 'Projections',
                showarrow: false,
                font: { color: '#3b82f6', size: 12 },
                yanchor: 'bottom',
              }
            ]
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: '100%' }}
        />
      </div>

      {/* Net Income Projections */}
      <div className="card mb-4">
        <div className="card-header">
          <h3 className="card-title">Projected Net Income</h3>
          <p className="card-subtitle">Historical and projected surplus/deficit (FY19-FY29)</p>
        </div>
        <Plot
          data={[
            {
              x: trends.financial_health.years,
              y: trends.financial_health.net_income,
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
              },
              {
                type: 'rect',
                xref: 'x',
                yref: 'paper',
                x0: 'FY26',
                x1: 'FY29',
                y0: 0,
                y1: 1,
                fillcolor: 'rgba(59, 130, 246, 0.1)',
                line: { width: 0 },
              }
            ],
            showlegend: false,
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: '100%' }}
        />
      </div>

      {/* Strategic Insights */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Strategic Financial Insights</h3>
          <p className="card-subtitle">Key observations and trends</p>
        </div>
        <div style={{ display: 'grid', gap: '1rem' }}>
          <div style={{ padding: '1rem', backgroundColor: 'rgba(16, 185, 129, 0.1)', borderRadius: '0.5rem', borderLeft: '4px solid #10b981' }}>
            <div style={{ fontWeight: '600', marginBottom: '0.5rem', color: '#10b981' }}>
              💰 Revenue Growth Trajectory
            </div>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-primary)' }}>
              Projected revenue growth from FY26 to FY29 shows a steady increase, driven by program expansion and enhanced fundraising efforts.
            </div>
          </div>
          <div style={{ padding: '1rem', backgroundColor: 'rgba(245, 158, 11, 0.1)', borderRadius: '0.5rem', borderLeft: '4px solid #f59e0b' }}>
            <div style={{ fontWeight: '600', marginBottom: '0.5rem', color: '#f59e0b' }}>
              📊 Program Performance
            </div>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-primary)' }}>
              Most programs are meeting or exceeding revenue goals, with strong performance in earned revenue categories.
            </div>
          </div>
          <div style={{ padding: '1rem', backgroundColor: 'rgba(59, 130, 246, 0.1)', borderRadius: '0.5rem', borderLeft: '4px solid #3b82f6' }}>
            <div style={{ fontWeight: '600', marginBottom: '0.5rem', color: '#3b82f6' }}>
              🎯 Financial Assistance Impact
            </div>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-primary)' }}>
              Total financial assistance of {formatCurrency(totalScholarships)} demonstrates strong commitment to accessibility and community impact.
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
