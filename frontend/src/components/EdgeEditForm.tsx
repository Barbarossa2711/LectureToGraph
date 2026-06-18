import { useState } from 'react'
import { EDGE_TYPES, EDGE_TYPE_LABELS } from '../types/graph'
import type { EdgeType } from '../types/graph'
import { createEdge, deleteEdge } from '../api/client'
import { usePipelineStore } from '../store/pipelineStore'

export default function EdgeEditForm() {
  const bumpViz = usePipelineStore((s) => s.bumpViz)
  const [source, setSource] = useState('')
  const [target, setTarget] = useState('')
  const [type, setType] = useState<EdgeType>('PREREQUISITE')
  const [msg, setMsg] = useState<string | null>(null)

  const add = async () => {
    if (!source || !target) return
    setMsg(null)
    try {
      await createEdge({ source_id: source, target_id: target, edge_type: type })
      bumpViz(); setSource(''); setTarget(''); setMsg('Kante gespeichert.')
    } catch (e: any) { setMsg(e?.response?.data?.detail ?? 'Fehler') }
  }

  const remove = async () => {
    if (!source || !target) return
    setMsg(null)
    try { await deleteEdge(source, target, type); bumpViz(); setMsg('Kante gelöscht.') }
    catch (e: any) { setMsg(e?.response?.data?.detail ?? 'Fehler') }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ fontSize: 12, fontWeight: 700 }}>Kante</div>
      <input style={inp} placeholder="Quell-ID" value={source} onChange={(e) => setSource(e.target.value)} />
      <input style={inp} placeholder="Ziel-ID" value={target} onChange={(e) => setTarget(e.target.value)} />
      <select style={inp} value={type} onChange={(e) => setType(e.target.value as EdgeType)}>
        {EDGE_TYPES.map((t) => <option key={t} value={t}>{EDGE_TYPE_LABELS[t]} ({t})</option>)}
      </select>
      <div style={{ display: 'flex', gap: 6 }}>
        <button style={btn('#6366f1')} onClick={add}>Hinzufügen</button>
        <button style={btn('#dc2626')} onClick={remove}>Löschen</button>
      </div>
      {msg && <div style={{ fontSize: 11, color: '#64748b' }}>{msg}</div>}
    </div>
  )
}

const inp: React.CSSProperties = {
  width: '100%', padding: '6px 8px', borderRadius: 5, border: '1px solid #d1d5db', fontSize: 12,
}
const btn = (bg: string): React.CSSProperties => ({
  flex: 1, padding: '6px 0', borderRadius: 5, border: 'none', cursor: 'pointer',
  background: bg, color: '#fff', fontSize: 12, fontWeight: 600,
})
