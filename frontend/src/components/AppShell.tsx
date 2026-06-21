import { Outlet } from 'react-router-dom'
import { AppSidebar } from '@/components/AppSidebar'
import './AppShell.css'

/** AppShell — admin layout: sidebar + topbar + scrollable <main>. */
export function AppShell() {
  return (
    <>
      <AppSidebar />
      <div className="main-column">
        <header className="topbar">
          <div className="topbar-title">
            <span className="topbar-emoji">👨‍🍳</span>
            <span className="topbar-text">Нейро-шеф Гурмикс</span>
          </div>
        </header>
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </>
  )
}
