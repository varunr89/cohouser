import React from 'react'
import Plot from 'react-plotly.js'

export default function SankeyChart({ data }) {
  if (!data) {
    return <div className="loading">Loading Sankey diagram...</div>
  }

  const layout = {
    title: {
      text: 'Revenue & Expense Flow',
      font: { size: 20, family: 'inherit' }
    },
    font: {
      size: 12,
      family: 'inherit'
    },
    height: 600,
    margin: { l: 20, r: 20, t: 60, b: 20 },
  }

  const trace = {
    type: 'sankey',
    orientation: 'h',
    node: {
      pad: 15,
      thickness: 20,
      line: {
        color: 'white',
        width: 1
      },
      label: data.labels,
      color: [
        '#10b981', // Contributions - green
        '#3b82f6', // Grants - blue
        '#8b5cf6', // Earned Revenue - purple
        '#f59e0b', // Events - orange
        '#ec4899', // Sponsorships - pink
        '#6366f1', // Other - indigo
        '#2c5f2d', // Organization - dark green
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
