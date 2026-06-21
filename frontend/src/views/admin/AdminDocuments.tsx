import { useEffect, useRef, useState } from 'react'
import { api } from '@/api'
import { useToast } from '@/components/Toast'
import './admin.css'

type DocRow = { id: number; title?: string; doc_type?: string; char_count?: number }

/** AdminDocuments — upload a file + list documents. Real ingestion in phase 2. */
export default function AdminDocuments() {
  const toast = useToast()
  const [docs, setDocs] = useState<DocRow[]>([])
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  function load() {
    api
      .adminGetDocuments()
      .then((r) => {
        const items = (r.data?.items ?? r.data) as DocRow[] | undefined
        if (Array.isArray(items)) setDocs(items)
      })
      .catch(() => {})
  }

  useEffect(load, [])

  async function upload(file: File) {
    setUploading(true)
    try {
      await api.adminUploadDocument(file)
      toast('Файл загружен', 'success')
      load()
    } catch {
      toast('Загрузка недоступна (фаза 2)', 'error')
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Документы</h1>
          <p className="admin-page-sub">Материалы для RAG-индекса.</p>
        </div>
        <div>
          <input
            ref={fileRef}
            type="file"
            style={{ display: 'none' }}
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) upload(f)
            }}
          />
          <button
            className="admin-btn admin-btn-primary"
            disabled={uploading}
            onClick={() => fileRef.current?.click()}
          >
            {uploading ? 'Загружаю…' : '+ Загрузить файл'}
          </button>
        </div>
      </div>
      <div className="admin-card">
        {docs.length === 0 ? (
          <div className="admin-empty">Документов пока нет.</div>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Тип</th>
                <th>Название</th>
                <th>Размер</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id}>
                  <td>{d.id}</td>
                  <td>{d.doc_type ?? '—'}</td>
                  <td>{d.title ?? '—'}</td>
                  <td>{d.char_count ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
