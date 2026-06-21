import { useEffect, useState } from 'react'
import { api } from '@/api'
import { useToast } from '@/components/Toast'
import './admin.css'

type ChunkRow = { id: number; document_id?: number; text?: string }

/** AdminChunks — list RAG chunks + rebuild index. Real data in phase 2. */
export default function AdminChunks() {
  const toast = useToast()
  const [chunks, setChunks] = useState<ChunkRow[]>([])
  const [rebuilding, setRebuilding] = useState(false)

  useEffect(() => {
    api
      .adminGetChunks()
      .then((r) => {
        const items = (r.data?.items ?? r.data) as ChunkRow[] | undefined
        if (Array.isArray(items)) setChunks(items)
      })
      .catch(() => {})
  }, [])

  async function rebuild() {
    setRebuilding(true)
    try {
      await api.adminRebuildIndex()
      toast('Индекс пересобирается', 'success')
    } catch {
      toast('Пересборка недоступна (фаза 2)', 'error')
    } finally {
      setRebuilding(false)
    }
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">RAG Чанки</h1>
          <p className="admin-page-sub">Фрагменты документов для поиска.</p>
        </div>
        <button className="admin-btn admin-btn-primary" disabled={rebuilding} onClick={rebuild}>
          {rebuilding ? 'Пересобираю…' : 'Пересобрать индекс'}
        </button>
      </div>
      <div className="admin-card">
        {chunks.length === 0 ? (
          <div className="admin-empty">Чанков пока нет.</div>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Документ</th>
                <th>Текст</th>
              </tr>
            </thead>
            <tbody>
              {chunks.map((c) => (
                <tr key={c.id}>
                  <td>{c.id}</td>
                  <td>{c.document_id ?? '—'}</td>
                  <td>{(c.text ?? '').slice(0, 120)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
