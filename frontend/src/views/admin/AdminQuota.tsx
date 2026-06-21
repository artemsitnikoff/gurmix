import { useEffect, useState } from 'react'
import { api } from '@/api'
import { useToast } from '@/components/Toast'
import './admin.css'

type QuotaConfig = { limit: number; period: 'day' | 'week' | 'month' }

/** AdminQuota — edit per-user request limit + reset period. */
export default function AdminQuota() {
  const toast = useToast()
  const [cfg, setCfg] = useState<QuotaConfig>({ limit: 30, period: 'day' })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api
      .adminGetQuotaConfig()
      .then((r) => {
        const d = r.data as Partial<QuotaConfig>
        if (d && typeof d.limit === 'number') {
          setCfg({ limit: d.limit, period: (d.period as QuotaConfig['period']) ?? 'day' })
        }
      })
      .catch(() => {})
  }, [])

  async function save() {
    setSaving(true)
    try {
      await api.adminUpdateQuotaConfig(cfg)
      toast('Лимиты сохранены', 'success')
    } catch {
      toast('Не удалось сохранить (фаза 2)', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Лимиты</h1>
          <p className="admin-page-sub">Квота запросов на пользователя (session + IP).</p>
        </div>
      </div>
      <div className="admin-card">
        <div style={{ display: 'flex', gap: 'var(--sp-4)', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-1)' }}>
            <span className="kpi-label">Лимит запросов</span>
            <input
              className="admin-input"
              type="number"
              min={1}
              value={cfg.limit}
              onChange={(e) => setCfg((c) => ({ ...c, limit: Number(e.target.value) }))}
            />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-1)' }}>
            <span className="kpi-label">Период сброса</span>
            <select
              className="admin-input"
              value={cfg.period}
              onChange={(e) =>
                setCfg((c) => ({ ...c, period: e.target.value as QuotaConfig['period'] }))
              }
            >
              <option value="day">День</option>
              <option value="week">Неделя</option>
              <option value="month">Месяц</option>
            </select>
          </label>
          <button className="admin-btn admin-btn-primary" disabled={saving} onClick={save}>
            {saving ? 'Сохраняю…' : 'Сохранить'}
          </button>
        </div>
      </div>
    </div>
  )
}
