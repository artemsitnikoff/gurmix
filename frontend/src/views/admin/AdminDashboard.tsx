import './admin.css'

/** AdminDashboard — KPI skeleton; real metrics wired in phase 2. */
export default function AdminDashboard() {
  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Dashboard</h1>
          <p className="admin-page-sub">Обзор базы знаний и активности.</p>
        </div>
      </div>
      <div className="admin-grid-kpi">
        <div className="kpi-card">
          <div className="kpi-label">Модули</div>
          <div className="kpi-value">8</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Активные</div>
          <div className="kpi-value">3</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Документы</div>
          <div className="kpi-value">—</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Запросов сегодня</div>
          <div className="kpi-value">—</div>
        </div>
      </div>
    </div>
  )
}
