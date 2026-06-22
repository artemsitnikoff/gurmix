import { useCallback, useEffect, useState } from 'react'
import { api } from '@/api'
import { renderAnswer } from '@/utils/sanitizeHtml'
import './admin.css'

type JournalRow = {
  id: number
  ts?: string
  session_id?: string
  module_id?: string
  question?: string
  answer?: string
  query_type?: string
  latency_ms?: number
  t_answer_model?: string
  top_score?: number | null
  chunks_used?: number
  feedback?: string | null
  feedback_note?: string | null
  usefulness_score?: number | null
  usefulness_verdict?: string | null
}

const PER_PAGE = 50
const FB_ICON: Record<string, string> = { good: '👍', bad: '👎' }

function usefulnessClass(s?: number | null): string {
  if (s == null) return ''
  if (s >= 75) return 'u-green'
  if (s >= 50) return 'u-yellow'
  return 'u-red'
}

function fmtTs(ts?: string): string {
  if (!ts) return '—'
  const d = new Date(ts)
  return isNaN(d.getTime()) ? ts : d.toLocaleString('ru-RU')
}

function Pill({ score, verdict }: { score?: number | null; verdict?: string | null }) {
  if (score == null) {
    return (
      <span className="u-pill u-pending" title="LLM-судья ещё не отработал">
        …
      </span>
    )
  }
  return (
    <span className={`u-pill ${usefulnessClass(score)}`} title={verdict ?? ''}>
      {score}
    </span>
  )
}

/** AdminJournal — лог запросов с оценкой LLM-судьи и просмотром диалога. */
export default function AdminJournal() {
  const [rows, setRows] = useState<JournalRow[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)
  const [selected, setSelected] = useState<JournalRow | null>(null)
  const [context, setContext] = useState<JournalRow[]>([])
  const [ctxLoading, setCtxLoading] = useState(false)

  const load = useCallback((p: number) => {
    setLoading(true)
    setErr(null)
    let alive = true
    api
      .adminGetJournal({ page: p, per_page: PER_PAGE })
      .then((r) => {
        if (!alive) return
        const data = r.data ?? {}
        const items = (data.items ?? data) as JournalRow[] | undefined
        setRows(Array.isArray(items) ? items : [])
        setTotal(typeof data.total === 'number' ? data.total : (items?.length ?? 0))
        setPage(typeof data.page === 'number' ? data.page : p)
      })
      .catch((e) => {
        if (!alive) return
        setErr(
          e?.response?.status === 401
            ? 'Нужна авторизация администратора.'
            : 'Не удалось загрузить журнал.',
        )
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => {
    const cleanup = load(1)
    return cleanup
  }, [load])

  function goto(p: number) {
    setSelected(null)
    setContext([])
    load(p)
  }

  async function openRow(r: JournalRow) {
    if (selected?.id === r.id) {
      setSelected(null)
      setContext([])
      return
    }
    setSelected(r)
    setContext([])
    if (!r.session_id) return
    setCtxLoading(true)
    try {
      const res = await api.adminGetJournalContext(r.id)
      const items = (res.data?.items ?? res.data) as JournalRow[] | undefined
      setContext(Array.isArray(items) ? items : [])
    } catch {
      setContext([])
    } finally {
      setCtxLoading(false)
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE))

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Журнал</h1>
          <p className="admin-page-sub">
            Лог запросов с оценкой LLM-судьи и диалогом{total ? ` · ${total} записей` : ''}.
          </p>
        </div>
      </div>

      <div className="admin-card">
        {loading ? (
          <div className="admin-empty">Загрузка…</div>
        ) : err ? (
          <div className="admin-empty">{err}</div>
        ) : rows.length === 0 ? (
          <div className="admin-empty">Записей пока нет.</div>
        ) : (
          <>
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Время</th>
                  <th>Модуль</th>
                  <th>Вопрос</th>
                  <th title="Оценка LLM-судьи 0–100">Судья</th>
                  <th>Оценка</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr
                    key={r.id}
                    className={`journal-row${selected?.id === r.id ? ' active' : ''}`}
                    onClick={() => openRow(r)}
                  >
                    <td>{fmtTs(r.ts)}</td>
                    <td>{r.module_id ?? '—'}</td>
                    <td>{(r.question ?? '').slice(0, 80)}</td>
                    <td>
                      <Pill score={r.usefulness_score} verdict={r.usefulness_verdict} />
                    </td>
                    <td>{r.feedback ? FB_ICON[r.feedback] ?? r.feedback : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {totalPages > 1 && (
              <div className="journal-pager">
                <button className="admin-btn" disabled={page <= 1} onClick={() => goto(page - 1)}>
                  ← Назад
                </button>
                <span className="journal-pager-info">
                  {page} / {totalPages}
                </span>
                <button
                  className="admin-btn"
                  disabled={page >= totalPages}
                  onClick={() => goto(page + 1)}
                >
                  Вперёд →
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {selected && (
        <div className="journal-detail admin-card">
          <div className="journal-detail-head">
            <strong>Запись #{selected.id}</strong>
            <button
              className="admin-btn"
              onClick={() => {
                setSelected(null)
                setContext([])
              }}
            >
              ✕
            </button>
          </div>

          {ctxLoading ? (
            <div className="admin-empty">Загрузка диалога…</div>
          ) : context.length > 0 ? (
            <div className="journal-section">
              <div className="journal-label">Диалог — предыдущие ходы</div>
              {context.map((t) => (
                <div key={t.id} className="dlg-turn">
                  <div className="dlg-q">{t.question}</div>
                  {t.answer && (
                    <div
                      className="dlg-a"
                      dangerouslySetInnerHTML={{ __html: renderAnswer(t.answer) }}
                    />
                  )}
                </div>
              ))}
            </div>
          ) : null}

          <div className="journal-section">
            <div className="journal-label">Вопрос</div>
            <div className="journal-q">{selected.question}</div>
          </div>

          <div className="journal-section">
            <div className="journal-label">
              Ответ
              {selected.t_answer_model ? ` · ${selected.t_answer_model}` : ''}
              {selected.latency_ms != null ? ` · ${(selected.latency_ms / 1000).toFixed(1)}с` : ''}
            </div>
            <div
              className="journal-a"
              dangerouslySetInnerHTML={{ __html: renderAnswer(selected.answer ?? '') }}
            />
          </div>

          <div className="journal-section">
            <div className="journal-label">⚖️ Оценка LLM-судьи</div>
            {selected.usefulness_score != null ? (
              <div>
                <Pill score={selected.usefulness_score} verdict={selected.usefulness_verdict} />
                {selected.usefulness_verdict && (
                  <span className="journal-verdict"> {selected.usefulness_verdict}</span>
                )}
              </div>
            ) : (
              <div className="admin-empty">Судья ещё не отработал (оценка приходит в фоне).</div>
            )}
          </div>

          {selected.feedback && (
            <div className="journal-section">
              <div className="journal-label">Оценка пользователя</div>
              <div>
                {FB_ICON[selected.feedback] ?? selected.feedback}
                {selected.feedback_note ? ` — ${selected.feedback_note}` : ''}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
