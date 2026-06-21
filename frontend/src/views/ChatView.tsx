import { useEffect, useMemo, useRef, useState } from 'react'
import { Navigate, useNavigate, useParams } from 'react-router-dom'
import { ChatMessage } from '@/components/ChatMessage'
import { api, sendChatStream } from '@/api'
import { getSessionId, resetSession } from '@/utils/chatSession'
import { MODULES_BY_ID } from '@/modules'
import type { ChatMessageModel, QuotaState } from '@/types'
import './ChatView.css'

/**
 * ChatView — chat for one module (`/m/:moduleId`). Header = emoji+title of
 * the module; empty-state examples come from module.examples. Streams via
 * sendChatStream; shows a «лимит исчерпан» banner on the `limit` event and a
 * remaining-quota indicator.
 */
export default function ChatView() {
  const { moduleId } = useParams<{ moduleId: string }>()
  const mod = moduleId ? MODULES_BY_ID[moduleId] : undefined
  const navigate = useNavigate()

  const [messages, setMessages] = useState<ChatMessageModel[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [quota, setQuota] = useState<QuotaState | null>(null)
  const [limitMsg, setLimitMsg] = useState<string | null>(null)

  const scrollRef = useRef<HTMLDivElement>(null)
  const taRef = useRef<HTMLTextAreaElement>(null)
  const sessionRef = useRef<string>(getSessionId())
  const idcRef = useRef(0)
  const nextId = () => ++idcRef.current

  // Reset conversation when switching modules.
  useEffect(() => {
    setMessages([])
    setInput('')
    setLimitMsg(null)
  }, [moduleId])

  // Pull current quota on mount / module change.
  useEffect(() => {
    let cancelled = false
    api
      .getQuota(sessionRef.current)
      .then((r) => {
        if (!cancelled) setQuota(r.data)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [moduleId])

  function scrollToBottom() {
    requestAnimationFrame(() => {
      const el = scrollRef.current
      if (el) el.scrollTop = el.scrollHeight
    })
  }

  function autoGrow() {
    const el = taRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 200) + 'px'
  }

  function resetTextarea() {
    const el = taRef.current
    if (el) el.style.height = 'auto'
  }

  function patch(id: number, fields: Partial<ChatMessageModel>) {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...fields } : m)))
  }

  async function send(textArg?: string) {
    const text = (textArg ?? input).trim()
    if (!text || sending || !mod) return

    // Last few completed turns (oldest first) for anaphora resolution.
    const history = messages
      .filter((m) => !m.pending && m.content && !m.isError)
      .slice(-6)
      .map((m) => ({ role: m.role, content: m.content }))

    setInput('')
    resetTextarea()

    const userId = nextId()
    const pendingId = nextId()
    setMessages((prev) => [
      ...prev,
      { id: userId, role: 'user', content: text },
      { id: pendingId, role: 'assistant', content: '', pending: true, phase: 'intent' },
    ])
    setSending(true)
    scrollToBottom()

    await sendChatStream(
      { module_id: mod.id, message: text, session_id: sessionRef.current, history },
      {
        onPhase: (phase) => {
          patch(pendingId, { phase: phase as ChatMessageModel['phase'] })
          scrollToBottom()
        },
        onDone: (ev) => {
          patch(pendingId, {
            pending: false,
            content: ev.answer_html || '',
            meta: ev.meta || null,
            logId: ev.log_id ?? null,
          })
          if (ev.quota) setQuota(ev.quota)
          setSending(false)
          scrollToBottom()
        },
        onLimit: (ev) => {
          // Drop the pending bubble; show the banner instead.
          setMessages((prev) => prev.filter((m) => m.id !== pendingId))
          setLimitMsg(ev.message || 'Лимит запросов исчерпан')
          if (ev.quota) setQuota(ev.quota)
          setSending(false)
          scrollToBottom()
        },
        onError: (err) => {
          patch(pendingId, {
            pending: false,
            isError: true,
            content:
              err?.message || 'Извините, не удалось получить ответ. Попробуйте ещё раз.',
          })
          setSending(false)
          scrollToBottom()
        },
      },
    )
  }

  function newChat() {
    if (sending) return
    setMessages([])
    sessionRef.current = resetSession()
    setInput('')
    setLimitMsg(null)
    resetTextarea()
    api
      .getQuota(sessionRef.current)
      .then((r) => setQuota(r.data))
      .catch(() => {})
  }

  const remaining = useMemo(() => {
    if (!quota) return null
    return Math.max(0, quota.remaining)
  }, [quota])

  // Unknown module → back to picker.
  if (!mod) return <Navigate to="/" replace />

  return (
    <div className="chat">
      <header className="chat-header">
        <div className="brand">
          <span className="brand-emoji">{mod.emoji}</span>
          <span className="brand-text">{mod.title}</span>
        </div>
        <div className="chat-header-right">
          {remaining != null && (
            <span className="quota-pill" title="Остаток запросов">
              Осталось: {remaining}/{quota?.limit}
            </span>
          )}
          <button className="back-btn" onClick={() => navigate('/')}>
            ← Эксперты
          </button>
          <button
            className="new-chat"
            disabled={sending || messages.length === 0}
            onClick={newChat}
          >
            + Новый диалог
          </button>
        </div>
      </header>

      {limitMsg && (
        <div className="limit-banner">
          ⛔ {limitMsg}
          {quota?.reset_at && (
            <span className="limit-reset">
              {' '}
              · сброс {new Date(quota.reset_at).toLocaleString('ru-RU')}
            </span>
          )}
        </div>
      )}

      <div ref={scrollRef} className="chat-scroll">
        <div className="chat-inner">
          {messages.length === 0 && (
            <div className="empty">
              <div className="empty-emoji">{mod.emoji}</div>
              <h1 className="empty-title">{mod.title}</h1>
              <p className="empty-sub">{mod.short}</p>
              <div className="examples">
                {mod.examples.map((ex) => (
                  <button key={ex} className="example" onClick={() => send(ex)}>
                    {ex}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m) => (
            <ChatMessage key={m.id} message={m} />
          ))}
        </div>
      </div>

      <div className="chat-input-bar">
        <div className="chat-input-inner">
          <div className="input-wrap">
            <textarea
              ref={taRef}
              value={input}
              className="chat-textarea"
              rows={1}
              placeholder="Спросите эксперта Гурмикс…"
              onChange={(e) => setInput(e.target.value)}
              onInput={autoGrow}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  send()
                }
              }}
            />
            <button
              className="send-btn"
              disabled={sending || !input.trim()}
              title="Отправить"
              onClick={() => send()}
            >
              {sending ? <span className="spin">⏳</span> : <span>➤</span>}
            </button>
          </div>
          <div className="input-hint">Enter — отправить · Shift+Enter — новая строка</div>
        </div>
      </div>
    </div>
  )
}
