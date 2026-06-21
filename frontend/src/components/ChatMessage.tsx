import { useMemo, useState } from 'react'
import { api } from '@/api'
import { sanitizeAnswer } from '@/utils/sanitizeHtml'
import { useToast } from '@/components/Toast'
import type { ChatMessageModel } from '@/types'
import './ChatMessage.css'

type Props = {
  message: ChatMessageModel
}

const PHASE_LABELS: Record<string, string> = {
  intent: 'Понимаю вопрос…',
  retrieval: 'Ищу в базе знаний…',
  answer: 'Формулирую ответ…',
}

/**
 * ChatMessage — user bubble or assistant block.
 * Assistant: phase indicator while pending, sanitized HTML answer,
 * meta-chip (score/timings), 👍/👎 feedback with inline note on 👎.
 */
export function ChatMessage({ message }: Props) {
  const toast = useToast()
  const isUser = message.role === 'user'
  const html = useMemo(() => sanitizeAnswer(message.content || ''), [message.content])
  const meta = message.meta || null

  const [feedback, setFeedback] = useState<'good' | 'bad' | null>(message.feedback ?? null)
  const [showNote, setShowNote] = useState(false)
  const [noteText, setNoteText] = useState('')
  const [done, setDone] = useState(false)
  const [sending, setSending] = useState(false)

  const phaseLabel = PHASE_LABELS[message.phase ?? ''] || 'Печатаю…'
  const scoreClass = useMemo(() => {
    const s = meta?.top_score
    if (s == null) return ''
    if (s >= 0.85) return 'score-green'
    if (s >= 0.8) return 'score-yellow'
    return 'score-red'
  }, [meta])

  async function rate(kind: 'good' | 'bad') {
    if (!message.logId || sending) return
    setFeedback(kind)
    try {
      await api.sendChatFeedback({ log_id: message.logId, feedback: kind })
    } catch {
      toast('Не удалось сохранить оценку', 'error')
    }
    if (kind === 'bad') setShowNote(true)
    else setDone(true)
  }

  async function submitNote() {
    if (sending || !message.logId) return
    setSending(true)
    try {
      await api.sendChatFeedback({
        log_id: message.logId,
        feedback: 'bad',
        note: noteText.trim() || null,
      })
      setDone(true)
      setShowNote(false)
    } catch {
      toast('Не удалось отправить', 'error')
    } finally {
      setSending(false)
    }
  }

  function skipNote() {
    setShowNote(false)
    setDone(true)
  }

  if (isUser) {
    return (
      <div className="msg msg-user">
        <div className="bubble-user">{message.content}</div>
      </div>
    )
  }

  return (
    <div className="msg msg-assistant">
      <div className="assistant-block">
        {message.pending ? (
          <div className="typing">
            <span className="dots">
              <span />
              <span />
              <span />
            </span>
            <span className="phase">{phaseLabel}</span>
          </div>
        ) : (
          <>
            <div className="answer" dangerouslySetInnerHTML={{ __html: html }} />

            {meta && (
              <div className="meta-chip">
                {meta.query_type && <span className="meta-type">{meta.query_type}</span>}
                {meta.top_score != null && (
                  <span className={`meta-score ${scoreClass}`}>
                    score {meta.top_score.toFixed(2)}
                  </span>
                )}
                {meta.chunks_used != null && <span>· {meta.chunks_used} фрагм.</span>}
                {meta.latency_ms != null && (
                  <span>· {(meta.latency_ms / 1000).toFixed(1)}с</span>
                )}
                {meta.t_answer_model && <span>· {meta.t_answer_model}</span>}
              </div>
            )}

            {message.logId != null && (
              <div className="fb-row">
                {!done ? (
                  <>
                    <button
                      className={feedback === 'good' ? 'fb-btn active' : 'fb-btn'}
                      title="Полезно"
                      onClick={() => rate('good')}
                    >
                      👍
                    </button>
                    <button
                      className={feedback === 'bad' ? 'fb-btn active' : 'fb-btn'}
                      title="Не то"
                      onClick={() => rate('bad')}
                    >
                      👎
                    </button>
                  </>
                ) : (
                  <span className="fb-thanks">Спасибо за оценку!</span>
                )}
              </div>
            )}

            {showNote && (
              <div className="note-box">
                <div className="note-label">
                  Что не так с ответом? Что нужно было ответить?
                </div>
                <textarea
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                  rows={3}
                  placeholder="Можно одним сообщением…"
                />
                <div className="note-actions">
                  <button className="btn btn-secondary" onClick={skipNote}>
                    Пропустить
                  </button>
                  <button className="btn btn-primary" disabled={sending} onClick={submitNote}>
                    {sending ? 'Отправляю…' : 'Отправить'}
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
