import { lazy, Suspense } from 'react'
import type { ReactNode } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import App from '@/App'

// Lazy-loaded views for code splitting.
const ModulePicker = lazy(() => import('@/views/ModulePicker'))
const ChatView = lazy(() => import('@/views/ChatView'))
const AdminModules = lazy(() => import('@/views/admin/AdminModules'))
const AdminQuota = lazy(() => import('@/views/admin/AdminQuota'))
const AdminDocuments = lazy(() => import('@/views/admin/AdminDocuments'))
const AdminChunks = lazy(() => import('@/views/admin/AdminChunks'))
const AdminDistributors = lazy(() => import('@/views/admin/AdminDistributors'))
const AdminJournal = lazy(() => import('@/views/admin/AdminJournal'))
const AdminDashboard = lazy(() => import('@/views/admin/AdminDashboard'))

function lazyEl(node: ReactNode): ReactNode {
  return <Suspense fallback={<div style={{ padding: 'var(--sp-6)' }}>Загрузка…</div>}>{node}</Suspense>
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      // Chat layout — main entry for experts (no admin shell).
      { index: true, element: lazyEl(<ModulePicker />), handle: { layout: 'chat' } },
      { path: 'm/:moduleId', element: lazyEl(<ChatView />), handle: { layout: 'chat' } },

      // Admin layout — knowledge-base + settings, under /admin.
      { path: 'admin', element: lazyEl(<AdminDashboard />), handle: { layout: 'admin' } },
      { path: 'admin/modules', element: lazyEl(<AdminModules />), handle: { layout: 'admin' } },
      { path: 'admin/quota', element: lazyEl(<AdminQuota />), handle: { layout: 'admin' } },
      { path: 'admin/documents', element: lazyEl(<AdminDocuments />), handle: { layout: 'admin' } },
      { path: 'admin/chunks', element: lazyEl(<AdminChunks />), handle: { layout: 'admin' } },
      { path: 'admin/distributors', element: lazyEl(<AdminDistributors />), handle: { layout: 'admin' } },
      { path: 'admin/journal', element: lazyEl(<AdminJournal />), handle: { layout: 'admin' } },
      { path: 'admin/*', element: <Navigate to="/admin" replace />, handle: { layout: 'admin' } },

      { path: '*', element: <Navigate to="/" replace />, handle: { layout: 'chat' } },
    ],
  },
])
