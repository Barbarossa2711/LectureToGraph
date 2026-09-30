import { useState } from 'react'
import type { JobSummary } from '../types/graph'
import { artifactUrl, fullCypherUrl, saveCypher } from '../api/client'
import { usePipelineStore } from '../store/pipelineStore'

/**
 * Buttons to save and download the graph as Cypher, plus the list of generated files.
 *
 * @param job The job.
 * @returns The export section, or null before anything was generated.
 */
export default function ExportButtons({ job }: { job: JobSummary }) {
  const { setJob } = usePipelineStore()
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const entries = Object.entries(job.artifacts)
  if (entries.length === 0 && !job.lecture_code) return null

  const save = async () => {
    setSaving(true)
    setSaved(false)
    try {
      const fresh = await saveCypher(job.id)
      setJob(fresh)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flexShrink: 0 }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: '#475569' }}>Cypher-Export</div>
      {job.lecture_code && (
        <>
          <button onClick={save} disabled={saving} style={{
            padding: '7px 0', borderRadius: 6, border: '1px solid #16a34a', cursor: 'pointer',
            background: '#16a34a', color: '#fff', fontWeight: 700, fontSize: 12,
          }}>
            {saving ? 'Speichere…' : saved ? '✓ Gespeichert' : '💾 Manuelle Änderungen in Cypher speichern'}
          </button>
          <a href={fullCypherUrl(job.id)} download
            style={{ fontSize: 12, color: '#16a34a', fontWeight: 700, textDecoration: 'none' }}>
            ↓ Aktueller Graph (inkl. manueller Änderungen)
          </a>
        </>
      )}
      {entries.length > 0 && (
        <div style={{
          display: 'flex', flexDirection: 'column', gap: 2,
          maxHeight: 180, overflowY: 'auto',
          border: '1px solid #eef2ff', borderRadius: 6, padding: '4px 6px',
        }}>
          {entries.map(([stage, paths]) => (
            <div key={stage} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {paths.map((p) => (
                <a key={p} href={artifactUrl(job.id, p)} download
                  style={{ fontSize: 12, color: '#4f46e5', textDecoration: 'none', wordBreak: 'break-all' }}>
                  ↓ {p}
                </a>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
