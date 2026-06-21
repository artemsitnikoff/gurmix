import { useEffect, useState } from 'react'
import { api } from '@/api'
import { MODULES } from '@/modules'
import type { BotModule } from '@/modules'
import { useToast } from '@/components/Toast'
import './admin.css'

/** AdminModules — list modules + status. Falls back to local manifest. */
export default function AdminModules() {
  const toast = useToast()
  const [modules, setModules] = useState<BotModule[]>(MODULES)

  useEffect(() => {
    api
      .adminGetModules()
      .then((r) => {
        const list = (r.data?.modules ?? r.data) as BotModule[] | undefined
        if (Array.isArray(list) && list.length) setModules(list)
      })
      .catch(() => {
        // Backend skeleton may 501 — keep the local manifest.
      })
  }, [])

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Модули</h1>
          <p className="admin-page-sub">Статус и режим 8 модулей-экспертов.</p>
        </div>
      </div>
      <div className="admin-card">
        <table className="admin-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Эмодзи</th>
              <th>Название</th>
              <th>Режим</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody>
            {[...modules]
              .sort((a, b) => a.order - b.order)
              .map((m) => (
                <tr key={m.id}>
                  <td>{m.order}</td>
                  <td>{m.emoji}</td>
                  <td>{m.title}</td>
                  <td>{m.mode}</td>
                  <td>
                    <button
                      className="admin-btn"
                      onClick={() => toast('Правка статуса — фаза 2', 'info')}
                    >
                      {m.status === 'active' ? 'Активен' : 'Скоро'}
                    </button>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
