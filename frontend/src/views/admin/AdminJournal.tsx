import { useEffect, useState } from 'react'
import { api } from '@/api'
import './admin.css'

type JournalRow = {
  id: number
  module_id?: string
  query?: string
  feedback?: string
  created_at?: string
}

/** AdminJournal — query log (port of teplodar query_logs). */
export default function AdminJournal() {
  const [rows, setRows] = useState<JournalRow[]>([])

  useEffect(() => {
    api
      .adminGetJournal()
      .then((r) => {
        const items = (r.data?.items ?? r.data) as JournalRow[] | undefined
        if (Array.isArray(items)) setRows(items)
      })
      .catch(() => {})
  }, [])

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Журнал</h1>
          <p className="admin-page-sub">Лог запросов пользователей.</p>
        </div>
      </div>
      <div className="admin-card">
        {rows.length === 0 ? (
          <div className="admin-empty">Записей пока нет.</div>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Модуль</th>
                <th>Запрос</th>
                <th>Оценка</th>
                <th>Время</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>{r.id}</td>
                  <td>{r.module_id ?? '—'}</td>
                  <td>{(r.query ?? '').slice(0, 80)}</td>
                  <td>{r.feedback ?? '—'}</td>
                  <td>{r.created_at ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
