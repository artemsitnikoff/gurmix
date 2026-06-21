import { useEffect, useState } from 'react'
import { api } from '@/api'
import { useToast } from '@/components/Toast'
import './admin.css'

type Distributor = {
  id: number
  name?: string
  region?: string
  city?: string
  phone?: string
}

/** AdminDistributors — directory for module 8 (db). CRUD skeleton. */
export default function AdminDistributors() {
  const toast = useToast()
  const [rows, setRows] = useState<Distributor[]>([])
  const [form, setForm] = useState({ name: '', region: '', city: '', phone: '' })
  const [saving, setSaving] = useState(false)

  function load() {
    api
      .adminGetDistributors()
      .then((r) => {
        const items = (r.data?.items ?? r.data) as Distributor[] | undefined
        if (Array.isArray(items)) setRows(items)
      })
      .catch(() => {})
  }

  useEffect(load, [])

  async function add() {
    if (!form.name.trim()) return
    setSaving(true)
    try {
      await api.adminCreateDistributor(form)
      toast('Дистрибьютор добавлен', 'success')
      setForm({ name: '', region: '', city: '', phone: '' })
      load()
    } catch {
      toast('Сохранение недоступно (фаза 2)', 'error')
    } finally {
      setSaving(false)
    }
  }

  async function remove(id: number) {
    try {
      await api.adminDeleteDistributor(id)
      load()
    } catch {
      toast('Удаление недоступно (фаза 2)', 'error')
    }
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Дистрибьюторы</h1>
          <p className="admin-page-sub">Подтверждённые контакты по регионам.</p>
        </div>
      </div>

      <div className="admin-card">
        <div style={{ display: 'flex', gap: 'var(--sp-2)', flexWrap: 'wrap' }}>
          <input
            className="admin-input"
            placeholder="Название"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          />
          <input
            className="admin-input"
            placeholder="Регион"
            value={form.region}
            onChange={(e) => setForm((f) => ({ ...f, region: e.target.value }))}
          />
          <input
            className="admin-input"
            placeholder="Город"
            value={form.city}
            onChange={(e) => setForm((f) => ({ ...f, city: e.target.value }))}
          />
          <input
            className="admin-input"
            placeholder="Телефон"
            value={form.phone}
            onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
          />
          <button className="admin-btn admin-btn-primary" disabled={saving} onClick={add}>
            + Добавить
          </button>
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
                <th>Название</th>
                <th>Регион</th>
                <th>Город</th>
                <th>Телефон</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((d) => (
                <tr key={d.id}>
                  <td>{d.id}</td>
                  <td>{d.name ?? '—'}</td>
                  <td>{d.region ?? '—'}</td>
                  <td>{d.city ?? '—'}</td>
                  <td>{d.phone ?? '—'}</td>
                  <td>
                    <button className="admin-btn" onClick={() => remove(d.id)}>
                      Удалить
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
