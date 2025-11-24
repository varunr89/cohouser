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
