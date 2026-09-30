import { useState } from 'react'
import type { JobSummary, Language } from '../types/graph'
import { setLanguage } from '../api/client'
import { usePipelineStore } from '../store/pipelineStore'

/**
 * Switch for the language the agent uses with the user.
 *
 * @param job The job.
 * @returns The switch.
 */
export default function LanguageToggle({ job }: { job: JobSummary }) {
  const { setJob } = usePipelineStore()
  const [busy, setBusy] = useState(false)

  const choose = async (l: Language) => {
    if (l === job.language || busy) return
    setBusy(true)
    try {
      const fresh = await setLanguage(job.id, l)
      setJob(fresh)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
      <span style={{ fontSize: 11, color: '#64748b', fontWeight: 600 }}>Sprache:</span>
      {(['de', 'en'] as Language[]).map((l) => (
        <button key={l} disabled={busy} onClick={() => choose(l)} style={{
          padding: '3px 10px', borderRadius: 999, cursor: 'pointer', fontSize: 11, fontWeight: 600,
          border: job.language === l ? '1px solid #6366f1' : '1px solid #e2e8f0',
          background: job.language === l ? '#eef2ff' : '#fff', color: job.language === l ? '#4338ca' : '#64748b',
        }}>
          {l === 'de' ? 'DE' : 'EN'}
        </button>
      ))}
    </div>
  )
}
