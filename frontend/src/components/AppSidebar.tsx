import { NavLink } from 'react-router-dom'
import { APP_VERSION } from '@/version'
import './AppSidebar.css'

type NavEntry = { to: string; icon: string; label: string; end?: boolean }

// Admin navigation per CONTRACT: Dashboard, Документы, RAG Чанки, Модули,
// Дистрибьюторы, Лимиты, Журнал.
const NAV: NavEntry[] = [
  { to: '/admin', icon: '📊', label: 'Dashboard', end: true },
  { to: '/admin/documents', icon: '📄', label: 'Документы' },
  { to: '/admin/chunks', icon: '🧩', label: 'RAG Чанки' },
  { to: '/admin/modules', icon: '📦', label: 'Модули' },
  { to: '/admin/distributors', icon: '📍', label: 'Дистрибьюторы' },
  { to: '/admin/quota', icon: '🎚️', label: 'Лимиты' },
  { to: '/admin/journal', icon: '📋', label: 'Журнал' },
]

/** AppSidebar — brand + admin nav. Active item: white bg + accent + shadow. */
export function AppSidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">
          <span className="brand-emoji">👨‍🍳</span>
        </div>
        <div className="brand-name">
          Нейро-шеф Гурмикс
          <span className="brand-version">v{APP_VERSION}</span>
        </div>
      </div>

      <nav className="nav">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
