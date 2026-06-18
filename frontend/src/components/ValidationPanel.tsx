import { useState } from 'react'
import type { JobSummary } from '../types/graph'
import { approveGate, rerunStage } from '../api/client'
import { usePipelineStore } from '../store/pipelineStore'
import NodeEditForm from './NodeEditForm'
import EdgeEditForm from './EdgeEditForm'

export default function ValidationPanel({ job }: { job: JobSummary }) {
  const { refreshJob } = usePipelineStore()
  const [feedback, setFeedback] = useState('')
  const [showEdit, setShowEdit] = useState(false)
  const [busy, setBusy] = useState(false)

  const approve = async () => {
    setBusy(true)
    try { await approveGate(job.id); await refreshJob() } finally { setBusy(false) }
  }

  const rerun = async () => {
    setBusy(true)
    try { await rerunStage(job.id, feedback || undefined); setFeedback(''); await refreshJob() }
    finally { setBusy(false) }
  }

  const last = job.status === 'COMPLETED'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <h3 style={{ margin: 0, fontSize: 15, color: '#6d28d9' }}>
        {last ? 'Pipeline abgeschlossen' : 'Schritt prüfen & validieren'}
      </h3>
      <p style={{ margin: 0, fontSize: 12, color: '#64748b' }}>
        Prüfe den Graphen links. Du kannst Knoten/Kanten manuell anpassen und dann
        freigeben oder den Schritt mit Feedback neu generieren lassen.
      </p>

      {!last && (
        <button onClick={approve} disabled={busy} style={{
          padding: '10px 0', borderRadius: 8, border: 'none', cursor: 'pointer',
          background: '#16a34a', color: '#fff', fontWeight: 700, fontSize: 14,
        }}>
          {busy ? '…' : 'Freigeben & weiter →'}
        </button>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <textarea placeholder="Feedback für eine Neugenerierung (optional)" value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          style={{ width: '100%', height: 54, padding: 8, borderRadius: 6, border: '1px solid #d1d5db', fontSize: 12 }} />
        <button onClick={rerun} disabled={busy} style={{
          padding: '8px 0', borderRadius: 7, border: '1px solid #c4b5fd', cursor: 'pointer',
          background: '#f5f3ff', color: '#6d28d9', fontWeight: 600, fontSize: 13,
        }}>
          Schritt neu generieren
        </button>
      </div>

      <button onClick={() => setShowEdit((v) => !v)} style={{
        padding: '6px 0', borderRadius: 6, border: '1px solid #e2e8f0', cursor: 'pointer',
        background: '#fff', fontSize: 12, color: '#475569',
      }}>
        {showEdit ? 'Manuellen Editor ausblenden' : 'Manuell bearbeiten'}
      </button>

      {showEdit && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, borderTop: '1px solid #e2e8f0', paddingTop: 10 }}>
          <NodeEditForm />
          <EdgeEditForm />
        </div>
      )}
    </div>
  )
}
