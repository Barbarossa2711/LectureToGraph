import { useEffect, useState } from 'react'
import { usePipelineStore } from '../store/pipelineStore'
import { createJob, uploadPdfs, startJob, getJob } from '../api/client'
import type { Language } from '../types/graph'

export default function JobSetup() {
  const { providers, loadProviders, setJob, connect } = usePipelineStore()
  const [provider, setProvider] = useState('')
  const [model, setModel] = useState('')
  const [language, setLang] = useState<Language>('de')
  const [files, setFiles] = useState<File[]>([])
  const [phase, setPhase] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => { loadProviders() }, [loadProviders])

  useEffect(() => {
    if (!provider && providers.length) {
      const first = providers.find((p) => p.available) ?? providers[0]
      setProvider(first.name)
      setModel(first.default_model ?? first.models[0]?.id ?? '')
    }
  }, [providers, provider])

  const current = providers.find((p) => p.name === provider)
  const busy = phase !== null

  const start = async () => {
    setErr(null)
    if (!files.length) { setErr('Bitte mindestens eine PDF auswählen.'); return }
    try {
      setPhase('Job wird angelegt…')
      const job = await createJob(provider, model, language)
      connect(job.id)                                  // capture events from the start
      setPhase('PDF(s) werden hochgeladen…')
      await uploadPdfs(job.id, files)
      setPhase('KI-Modus wird gestartet…')
      await startJob(job.id)
      const fresh = await getJob(job.id)
      setJob(fresh)                                    // hand over to the pipeline view only now
    } catch (e: any) {
      setErr(e?.response?.data?.detail ?? e?.message ?? 'Fehler beim Start')
      setPhase(null)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <h2 style={{ margin: 0, fontSize: 16 }}>KI-Modus: PDF → Wissensgraph</h2>

      <label style={lbl}>KI-Anbieter</label>
      <select style={inp} value={provider} disabled={busy} onChange={(e) => {
        setProvider(e.target.value)
        const p = providers.find((x) => x.name === e.target.value)
        setModel(p?.default_model ?? p?.models[0]?.id ?? '')
      }}>
        {providers.map((p) => (
          <option key={p.name} value={p.name} disabled={!p.available}>
            {p.label}{p.available ? '' : ' (kein API-Key)'}
          </option>
        ))}
      </select>

      <label style={lbl}>Modell</label>
      <select style={inp} value={model} disabled={busy} onChange={(e) => setModel(e.target.value)}>
        {current?.models.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
      </select>

      <label style={lbl}>Sprache der KI-Rückfragen</label>
      <div style={{ display: 'flex', gap: 6 }}>
        {(['de', 'en'] as Language[]).map((l) => (
          <button key={l} type="button" disabled={busy} onClick={() => setLang(l)} style={{
            flex: 1, padding: '7px 0', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 600,
            border: language === l ? '1px solid #6366f1' : '1px solid #d1d5db',
            background: language === l ? '#eef2ff' : '#fff', color: language === l ? '#4338ca' : '#475569',
          }}>
            {l === 'de' ? 'Deutsch' : 'English'}
          </button>
        ))}
      </div>

      <label style={lbl}>Vorlesungs-PDF(s)</label>
      <input style={inp} type="file" accept="application/pdf" multiple disabled={busy}
        onChange={(e) => setFiles(Array.from(e.target.files ?? []))} />
      {files.length > 0 && (
        <div style={{ fontSize: 12, color: '#64748b' }}>{files.map((f) => f.name).join(', ')}</div>
      )}

      {err && <div style={{ color: '#dc2626', fontSize: 12 }}>{err}</div>}
      {phase && <div style={{ color: '#2563eb', fontSize: 12 }}>{phase}</div>}

      <button onClick={start} disabled={busy || !current?.available} style={{
        padding: '10px 0', borderRadius: 8, border: 'none', cursor: busy ? 'default' : 'pointer',
        background: busy ? '#94a3b8' : '#6366f1', color: '#fff', fontWeight: 700, fontSize: 14,
      }}>
        {busy ? phase : 'KI-Modus starten'}
      </button>
    </div>
  )
}

const lbl: React.CSSProperties = { fontSize: 12, fontWeight: 600, color: '#374151' }
const inp: React.CSSProperties = {
  width: '100%', padding: '8px 9px', borderRadius: 6,
  border: '1px solid #d1d5db', fontSize: 13, background: '#fff',
}
