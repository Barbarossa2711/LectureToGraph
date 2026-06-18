import { useState } from 'react'
import type { JobSummary } from '../types/graph'
import { addChapter, finishJob, uploadPdfs } from '../api/client'
import { usePipelineStore } from '../store/pipelineStore'

export default function NextChapterPanel({ job }: { job: JobSummary }) {
  const { refreshJob } = usePipelineStore()
  const [files, setFiles] = useState<File[]>([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const addNext = async () => {
    setBusy(true); setErr(null)
    try {
      if (files.length) await uploadPdfs(job.id, files)
      await addChapter(job.id)
      setFiles([])
      await refreshJob()
    } catch (e: any) {
      setErr(e?.response?.data?.detail ?? e?.message ?? 'Fehler'); setBusy(false)
    }
  }

  const done = async () => {
    setBusy(true); setErr(null)
    try { await finishJob(job.id); await refreshJob() }
    catch (e: any) { setErr(e?.response?.data?.detail ?? 'Fehler'); setBusy(false) }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <h3 style={{ margin: 0, fontSize: 15, color: '#6d28d9' }}>
        Kapitel {job.chapter_no} fertig
      </h3>
      <p style={{ margin: 0, fontSize: 12, color: '#64748b' }}>
        Du kannst ein weiteres Kapitel hinzufügen oder die Vorlesung abschließen.
        Für ein neues Kapitel-PDF dieses unten auswählen — bei einem Gesamt-Dokument
        einfach ohne Upload „Weiteres Kapitel" klicken, dann wird das nächste Kapitel
        daraus verarbeitet.
      </p>

      <label style={{ fontSize: 12, fontWeight: 600, color: '#374151' }}>
        Neues Kapitel-PDF (optional)
      </label>
      <input type="file" accept="application/pdf" multiple disabled={busy}
        onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
        style={{ fontSize: 12 }} />
      {files.length > 0 && (
        <div style={{ fontSize: 11, color: '#64748b' }}>{files.map((f) => f.name).join(', ')}</div>
      )}

      <button onClick={addNext} disabled={busy} style={{
        padding: '10px 0', borderRadius: 8, border: 'none', cursor: 'pointer',
        background: busy ? '#94a3b8' : '#6366f1', color: '#fff', fontWeight: 700, fontSize: 14,
      }}>
        {busy ? '…' : '+ Weiteres Kapitel hinzufügen'}
      </button>

      <button onClick={done} disabled={busy} style={{
        padding: '9px 0', borderRadius: 8, border: '1px solid #16a34a', cursor: 'pointer',
        background: '#fff', color: '#16a34a', fontWeight: 700, fontSize: 13,
      }}>
        ✓ Vorlesung abschließen
      </button>

      {err && <div style={{ fontSize: 12, color: '#dc2626' }}>{err}</div>}
    </div>
  )
}
