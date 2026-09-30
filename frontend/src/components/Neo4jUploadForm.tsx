import { useEffect, useState } from 'react'
import type { JobSummary } from '../types/graph'
import { uploadToNeo4j, loadBundled, getBundledAccess, type BundledAccess } from '../api/client'

/**
 * Neo4j section: access to the bundled database and upload into an own database.
 *
 * @param job The job.
 * @returns The section, or null before a graph exists.
 */
export default function Neo4jUploadForm({ job }: { job: JobSummary }) {
  if (!job.lecture_code) return null
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, flexShrink: 0 }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: '#475569' }}>Neo4j</div>
      <BundledSection job={job} />
      <OwnDbSection job={job} />
    </div>
  )
}

/**
 * Connection data of the bundled Docker Neo4j and a button to load the graph into it again.
 *
 * @param job The job.
 * @returns The section.
 */
function BundledSection({ job }: { job: JobSummary }) {
  const [open, setOpen] = useState(true)
  const [access, setAccess] = useState<BundledAccess | null>(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  useEffect(() => { getBundledAccess(job.id).then(setAccess).catch(() => {}) }, [job.id])

  const reload = async () => {
    setBusy(true); setMsg(null)
    try {
      const r = await loadBundled(job.id)
      setMsg({ ok: true, text: `✓ Geladen: ${r.statements} Statements, ${r.constraints} Constraints` })
    } catch (e: any) {
      setMsg({ ok: false, text: e?.response?.data?.detail ?? e?.message ?? 'Fehler' })
    } finally { setBusy(false) }
  }

  const sample = `MATCH (n) WHERE n.id STARTS WITH '${job.lecture_code}'\nOPTIONAL MATCH (n)-[r]->(m) WHERE m.id STARTS WITH '${job.lecture_code}'\nRETURN n, r, m`

  return (
    <div style={card}>
      <button onClick={() => setOpen((v) => !v)} style={head}>
        {open ? '▾' : '▸'} Mitgelieferte Neo4j (Docker)
      </button>
      {open && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <p style={hint}>
            Der Graph liegt bereits in der mitgelieferten Neo4j (sie speist die Visualisierung).
            So erreichst du sie vom Browser aus:
          </p>
          <div style={kv}><span style={k}>Neo4j Browser</span>
            <a href={access?.browser_http ?? 'http://localhost:7474'} target="_blank" rel="noreferrer"
              style={{ color: '#2563eb', fontSize: 11 }}>
              {access?.browser_http ?? 'http://localhost:7474'} ↗
            </a>
          </div>
          <div style={kv}><span style={k}>Bolt</span><code style={code}>{access?.bolt_uri ?? 'bolt://localhost:7687'}</code></div>
          <div style={kv}><span style={k}>Login</span><code style={code}>{(access?.user ?? 'neo4j')} / {(access?.password ?? 'password')}</code></div>
          <div style={{ fontSize: 11, color: '#64748b' }}>Beispiel-Abfrage (zum Kopieren):</div>
          <textarea readOnly value={sample} onFocus={(e) => e.currentTarget.select()}
            style={{ width: '100%', height: 56, fontSize: 10.5, fontFamily: 'monospace',
              padding: 6, borderRadius: 5, border: '1px solid #e2e8f0', background: '#f8fafc' }} />
          <button onClick={reload} disabled={busy} style={primaryBtn('#6366f1')}>
            {busy ? 'Lädt…' : 'Erneut in mitgelieferte DB laden'}
          </button>
          {msg && <div style={{ fontSize: 11, color: msg.ok ? '#166534' : '#dc2626' }}>{msg.text}</div>}
        </div>
      )}
    </div>
  )
}

/**
 * Form to upload the graph into the user's own Neo4j, e.g. Neo4j Desktop.
 *
 * @param job The job.
 * @returns The section.
 */
function OwnDbSection({ job }: { job: JobSummary }) {
  const [open, setOpen] = useState(false)
  const [uri, setUri] = useState('bolt://127.0.0.1:7687')
  const [user, setUser] = useState('neo4j')
  const [password, setPassword] = useState('')
  const [database, setDatabase] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const submit = async () => {
    setBusy(true); setMsg(null)
    try {
      const r = await uploadToNeo4j(job.id, { uri, user, password, database: database || undefined })
      setMsg({ ok: true, text: `✓ Hochgeladen: ${r.statements} Statements, ${r.constraints} Constraints` })
    } catch (e: any) {
      setMsg({ ok: false, text: e?.response?.data?.detail ?? e?.message ?? 'Upload fehlgeschlagen' })
    } finally { setBusy(false) }
  }

  return (
    <div style={card}>
      <button onClick={() => setOpen((v) => !v)} style={head}>
        {open ? '▾' : '▸'} Eigene Neo4j (Desktop / eigener Docker)
      </button>
      {open && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <p style={hint}>
            Lädt den aktuellen Graphen (inkl. manueller Änderungen) in eine eigene Neo4j.
            Für eine DB auf <b>deinem Rechner</b> einfach <code>localhost</code> / <code>127.0.0.1</code>
            eintragen — das wird automatisch auf den Host umgeleitet. Achtung: Port <code>7687</code>
            ist auch von der mitgelieferten DB belegt; nutze ggf. den Port deiner eigenen DB.
          </p>
          <input style={inp} placeholder="bolt://127.0.0.1:7687" value={uri} onChange={(e) => setUri(e.target.value)} />
          <input style={inp} placeholder="Benutzer" value={user} onChange={(e) => setUser(e.target.value)} />
          <input style={inp} type="password" placeholder="Passwort" value={password} onChange={(e) => setPassword(e.target.value)} />
          <input style={inp} placeholder="Datenbank (optional)" value={database} onChange={(e) => setDatabase(e.target.value)} />
          <button onClick={submit} disabled={busy || !uri || !user} style={primaryBtn('#0ea5e9')}>
            {busy ? 'Lädt hoch…' : 'Hochladen'}
          </button>
          {msg && <div style={{ fontSize: 11, color: msg.ok ? '#166534' : '#dc2626' }}>{msg.text}</div>}
        </div>
      )}
    </div>
  )
}

const card: React.CSSProperties = {
  display: 'flex', flexDirection: 'column', gap: 6,
  border: '1px solid #e2e8f0', borderRadius: 6, padding: 8,
}
const head: React.CSSProperties = {
  textAlign: 'left', border: 'none', background: 'transparent', cursor: 'pointer',
  fontSize: 12, fontWeight: 600, color: '#334155', padding: 0,
}
const hint: React.CSSProperties = { margin: 0, fontSize: 11, color: '#64748b', lineHeight: 1.4 }
const kv: React.CSSProperties = { display: 'flex', gap: 6, alignItems: 'baseline' }
const k: React.CSSProperties = { fontSize: 11, color: '#94a3b8', width: 78, flexShrink: 0 }
const code: React.CSSProperties = { fontSize: 11, color: '#0f172a' }
const inp: React.CSSProperties = {
  width: '100%', padding: '6px 8px', borderRadius: 5,
  border: '1px solid #d1d5db', fontSize: 12, background: '#fff',
}
const primaryBtn = (bg: string): React.CSSProperties => ({
  padding: '8px 0', borderRadius: 6, border: 'none', cursor: 'pointer',
  background: bg, color: '#fff', fontWeight: 700, fontSize: 12,
})
