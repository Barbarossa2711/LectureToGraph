import { STAGES } from '../types/graph'
import type { JobSummary } from '../types/graph'

const STATUS_LABEL: Record<string, string> = {
  CREATED: 'erstellt',
  UPLOADED: 'hochgeladen',
  RUNNING: 'läuft…',
  AWAITING_USER_INPUT: 'wartet auf Antwort',
  AWAITING_VALIDATION: 'zur Prüfung',
  AWAITING_NEXT_CHAPTER: 'Kapitel fertig',
  COMPLETED: 'fertig',
  FAILED: 'Fehler',
}

const STATUS_COLOR: Record<string, string> = {
  RUNNING: '#2563eb',
  AWAITING_USER_INPUT: '#d97706',
  AWAITING_VALIDATION: '#7c3aed',
  COMPLETED: '#16a34a',
  FAILED: '#dc2626',
}

/**
 * Shows the three stages with the active one highlighted, plus status, chapter and error.
 *
 * @param job The job.
 * @returns The stepper.
 */
export default function PipelineStepper({ job }: { job: JobSummary }) {
  const activeIdx = STAGES.findIndex((s) => s.key === job.stage)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, flexShrink: 0 }}>
      <div style={{ display: 'flex', gap: 6 }}>
        {STAGES.map((s, i) => {
          const done = i < activeIdx || job.status === 'COMPLETED'
          const active = i === activeIdx && job.status !== 'COMPLETED'
          return (
            <div key={s.key} style={{
              flex: 1, padding: '8px 6px', borderRadius: 6, textAlign: 'center',
              fontSize: 11, fontWeight: 700,
              background: done ? '#dcfce7' : active ? '#ede9fe' : '#f1f5f9',
              color: done ? '#166534' : active ? '#6d28d9' : '#94a3b8',
              border: active ? '1px solid #a78bfa' : '1px solid transparent',
            }}>
              {i + 1}. {s.label}
            </div>
          )
        })}
      </div>
      <div style={{ fontSize: 12 }}>
        Status:{' '}
        <span style={{ fontWeight: 700, color: STATUS_COLOR[job.status] ?? '#334155' }}>
          {STATUS_LABEL[job.status] ?? job.status}
        </span>
        <span style={{ color: '#94a3b8' }}> · Kapitel {job.chapter_no}</span>
        {job.lecture_code && (
          <span style={{ color: '#94a3b8' }}> · {job.lecture_code}</span>
        )}
      </div>
      {job.error && <div style={{ fontSize: 12, color: '#dc2626' }}>{job.error}</div>}
    </div>
  )
}
