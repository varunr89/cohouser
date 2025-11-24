import React, { useState, useEffect } from 'react'
import Plot from 'react-plotly.js'

export default function ExpensePage() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [data, setData] = useState({
    expenses: null,
    trends: null,
  })

  useEffect(() => {
    const loadData = async () => {
      try {
        const [expenseRes, trendsRes] = await Promise.all([
          fetch('/cohouser/data/expense_data.json'),
          fetch('/cohouser/data/historical_trends.json'),
        ])

        const expenses = await expenseRes.json()
        const trends = await trendsRes.json()

        setData({ expenses, trends })
        setLoading(false)
      } catch (err) {
        setError(err.message)
        setLoading(false)
      }
    }

    loadData()
  }, [])

  if (loading) {
    return <div className="loading">Loading expense data...</div>
  }

  if (error) {
    return <div className="error">Error loading data: {error}</div>
  }

  const { expenses, trends } = data

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

  // Calculate payroll vs operations split
  const payrollTotal = expenses.salaries_wages.actual + expenses.payroll_taxes.actual + expenses.benefits.actual
  const operationsTotal = expenses.total.actual - payrollTotal

  return (
    <div>
      <div className="mb-4">
        <h2 style={{ fontSize: '1.875rem', fontWeight: '700', marginBottom: '0.5rem' }}>
          Expense Analysis
        </h2>
        <p style={{ color: 'var(--text-secondary)' }}>
          Detailed breakdown of organizational expenses and budget tracking
        </p>
      </div>

      {/* Total Expense Summary */}
      <div className="card mb-4">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
              TOTAL EXPENSES (YTD)
            </div>
            <div style={{ fontSize: '2.5rem', fontWeight: '700' }}>
              {formatCurrency(expenses.total.actual)}
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
              BUDGET
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--text-secondary)' }}>
              {formatCurrency(expenses.total.budgeted)}
            </div>
            <div style={{ fontSize: '0.875rem', color: calculateVariance(expenses.total.actual, expenses.total.budgeted) <= 0 ? 'var(--success-color)' : 'var(--danger-color)', marginTop: '0.5rem' }}>
              {calculateVariance(expenses.total.actual, expenses.total.budgeted) >= 0 ? '▲' : '▼'} {Math.abs(calculateVariance(expenses.total.actual, expenses.total.budgeted)).toFixed(1)}% vs budget
            </div>
          </div>
        </div>
      </div>

      {/* Payroll vs Operations */}
      <div className="grid-2 mb-4">
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Expense Split</h3>
            <p className="card-subtitle">Payroll vs Operating Expenses</p>
          </div>
          <Plot
            data={[
              {
                type: 'pie',
                labels: ['Payroll & Benefits', 'Operations'],
                values: [payrollTotal, operationsTotal],
                marker: {
                  colors: ['#ef4444', '#f97316']
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
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginTop: '1rem' }}>
            <div style={{ textAlign: 'center', padding: '1rem', backgroundColor: 'rgba(239, 68, 68, 0.1)', borderRadius: '0.5rem' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>PAYROLL</div>
              <div style={{ fontSize: '1.25rem', fontWeight: '700', color: '#ef4444' }}>{formatCurrency(payrollTotal)}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                {((payrollTotal / expenses.total.actual) * 100).toFixed(1)}% of total
              </div>
            </div>
            <div style={{ textAlign: 'center', padding: '1rem', backgroundColor: 'rgba(249, 115, 22, 0.1)', borderRadius: '0.5rem' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>OPERATIONS</div>
              <div style={{ fontSize: '1.25rem', fontWeight: '700', color: '#f97316' }}>{formatCurrency(operationsTotal)}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                {((operationsTotal / expenses.total.actual) * 100).toFixed(1)}% of total
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Payroll Budget Tracking</h3>
            <p className="card-subtitle">Salaries, taxes, and benefits</p>
          </div>
          <Plot
            data={[
              {
                x: ['Salaries & Wages', 'Payroll Taxes', 'Benefits'],
                y: [
                  expenses.salaries_wages.budgeted,
                  expenses.payroll_taxes.budgeted,
                  expenses.benefits.budgeted,
                ],
                name: 'Budgeted',
                type: 'bar',
                marker: { color: 'rgba(100, 116, 139, 0.5)' },
              },
              {
                x: ['Salaries & Wages', 'Payroll Taxes', 'Benefits'],
                y: [
                  expenses.salaries_wages.actual,
                  expenses.payroll_taxes.actual,
                  expenses.benefits.actual,
                ],
                name: 'Actual',
                type: 'bar',
                marker: { color: '#ef4444' },
              },
            ]}
            layout={{
              height: 400,
              margin: { l: 60, r: 20, t: 20, b: 60 },
              xaxis: { tickangle: -45 },
              yaxis: { title: 'Amount ($)', tickformat: '$,.0f' },
              barmode: 'group',
              legend: { orientation: 'h', y: -0.25 },
              font: { family: 'inherit' },
            }}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%' }}
          />
        </div>
      </div>

      {/* Detailed Expense Breakdown */}
      <div className="card mb-4">
        <div className="card-header">
          <h3 className="card-title">Detailed Expense Breakdown</h3>
          <p className="card-subtitle">Budget vs actual with variance analysis</p>
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
              {Object.entries(expenses).filter(([key]) => key !== 'total').map(([key, values]) => {
                const variance = calculateVariance(values.actual, values.budgeted)
                const percentOfTotal = (values.actual / expenses.total.actual) * 100
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
                    <td style={{ padding: '0.75rem', textAlign: 'right', color: variance <= 0 ? 'var(--success-color)' : 'var(--danger-color)', fontWeight: '600' }}>
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
                  {formatCurrency(expenses.total.budgeted)}
                </td>
                <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                  {formatCurrency(expenses.total.actual)}
                </td>
                <td style={{ padding: '0.75rem', textAlign: 'right', color: calculateVariance(expenses.total.actual, expenses.total.budgeted) <= 0 ? 'var(--success-color)' : 'var(--danger-color)' }}>
                  {calculateVariance(expenses.total.actual, expenses.total.budgeted) >= 0 ? '+' : ''}{calculateVariance(expenses.total.actual, expenses.total.budgeted).toFixed(1)}%
                </td>
                <td style={{ padding: '0.75rem', textAlign: 'right' }}>100.0%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Historical Trends */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Multi-Year Expense Trends</h3>
          <p className="card-subtitle">Historical performance (FY19-FY26)</p>
        </div>
        <Plot
          data={[
            {
              x: trends.expense_trends.years,
              y: trends.expense_trends.salaries_wages_benefits,
              name: 'Payroll & Benefits',
              type: 'scatter',
              mode: 'lines+markers',
              stackgroup: 'one',
              line: { color: '#ef4444', width: 0 },
              fillcolor: 'rgba(239, 68, 68, 0.7)',
            },
            {
              x: trends.expense_trends.years,
              y: trends.expense_trends.operating_expenses,
              name: 'Operating Expenses',
              type: 'scatter',
              mode: 'lines+markers',
              stackgroup: 'one',
              line: { color: '#f97316', width: 0 },
              fillcolor: 'rgba(249, 115, 22, 0.7)',
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
