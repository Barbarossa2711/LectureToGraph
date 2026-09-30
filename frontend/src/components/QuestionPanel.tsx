import { useEffect, useState } from 'react'
import type { AskUserPayload } from '../types/graph'
import { answerQuestion } from '../api/client'
import { usePipelineStore } from '../store/pipelineStore'

/**
 * Shows the agent's questions with answer options or free text and sends the answers.
 *
 * @param jobId The job id.
 * @param payload The pending questions.
 * @returns The panel.
 */
export default function QuestionPanel({ jobId, payload }: { jobId: string; payload: AskUserPayload }) {
  const { refreshJob } = usePipelineStore()
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)

  useEffect(() => { setAnswers({}) }, [payload])

  const submit = async () => {
    setBusy(true)
    try {
      await answerQuestion(jobId, answers)
      await refreshJob()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <h3 style={{ margin: 0, fontSize: 15, color: '#b45309' }}>Die KI hat Rückfragen</h3>
      {payload.questions.map((q, i) => (
        <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ fontSize: 13, fontWeight: 600 }}>{q.question}</div>
          {q.options && q.options.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {q.options.map((opt) => {
                const selected = answers[q.header] === opt.label
                return (
                  <button key={opt.label} onClick={() => setAnswers((a) => ({ ...a, [q.header]: opt.label }))}
                    style={{
                      textAlign: 'left', padding: '7px 9px', borderRadius: 6, cursor: 'pointer',
                      border: selected ? '2px solid #6366f1' : '1px solid #d1d5db',
                      background: selected ? '#eef2ff' : '#fff', fontSize: 12,
                    }}>
                    <div style={{ fontWeight: 700 }}>{opt.label}</div>
                    {opt.description && <div style={{ color: '#64748b' }}>{opt.description}</div>}
                  </button>
                )
              })}
              <input placeholder="oder eigene Antwort…" style={inp}
                onChange={(e) => setAnswers((a) => ({ ...a, [q.header]: e.target.value }))} />
            </div>
          ) : (
            <textarea style={{ ...inp, height: 60 }} value={answers[q.header] ?? ''}
              onChange={(e) => setAnswers((a) => ({ ...a, [q.header]: e.target.value }))} />
          )}
        </div>
      ))}
      <button onClick={submit} disabled={busy} style={{
        padding: '9px 0', borderRadius: 7, border: 'none', cursor: 'pointer',
        background: '#d97706', color: '#fff', fontWeight: 700, fontSize: 13,
      }}>
        {busy ? 'Sendet…' : 'Antwort senden'}
      </button>
    </div>
  )
}

const inp: React.CSSProperties = {
  width: '100%', padding: '7px 9px', borderRadius: 6,
  border: '1px solid #d1d5db', fontSize: 12, background: '#fff',
}
