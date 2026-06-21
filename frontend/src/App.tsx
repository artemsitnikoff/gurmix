import { Outlet, useMatches } from 'react-router-dom'
import { AppShell } from '@/components/AppShell'
import { ToastProvider } from '@/components/Toast'
import './App.css'

type RouteHandle = { layout?: 'chat' | 'admin' }

/**
 * App — picks the layout from the active route's handle.meta.
 * chat: full-screen, no sidebar, mobile-friendly.
 * admin: 240px sidebar grid + 52px topbar, desktop min-width.
 * Toasts render top-right via ToastProvider.
 */
export default function App() {
  const matches = useMatches()
  const isChat = matches.some((m) => (m.handle as RouteHandle | undefined)?.layout === 'chat')

  return (
    <ToastProvider>
      <div className={isChat ? 'app-chat' : 'app'}>
        {isChat ? <Outlet /> : <AppShell />}
      </div>
    </ToastProvider>
  )
}
