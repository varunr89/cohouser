import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom'
import ExecutiveSummary from './pages/ExecutiveSummary'
import RevenuePage from './pages/RevenuePage'
import ExpensePage from './pages/ExpensePage'
import CashFlowPage from './pages/CashFlowPage'
import ProgramsPage from './pages/ProgramsPage'
import './App.css'

function App() {
  return (
    <Router basename="/cohouser">
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
              <li>
                <NavLink to="/" className="nav-link" end>
                  📊 Executive Summary
                </NavLink>
              </li>
              <li>
                <NavLink to="/revenue" className="nav-link">
                  💰 Revenue Analysis
                </NavLink>
              </li>
              <li>
                <NavLink to="/expenses" className="nav-link">
                  📉 Expense Analysis
                </NavLink>
              </li>
              <li>
                <NavLink to="/cashflow" className="nav-link">
                  🔄 Cash Flow & Reserves
                </NavLink>
              </li>
              <li>
                <NavLink to="/programs" className="nav-link">
                  🎯 Programs & Planning
                </NavLink>
              </li>
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
