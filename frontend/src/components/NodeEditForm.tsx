import { useState } from 'react'
import { NODE_TYPES, NODE_TYPE_LABELS } from '../types/graph'
import type { NodeType } from '../types/graph'
import { createNode, deleteNode } from '../api/client'
import { usePipelineStore } from '../store/pipelineStore'

export default function NodeEditForm() {
  const bumpViz = usePipelineStore((s) => s.bumpViz)
  const [id, setId] = useState('')
  const [type, setType] = useState<NodeType>('Concept')
  const [parentId, setParentId] = useState('')
  const [name, setName] = useState('')
  const [msg, setMsg] = useState<string | null>(null)

  const add = async () => {
    if (!id) return
    setMsg(null)
    try {
      const props: Record<string, unknown> = {}
      if (name) props[type === 'Question' ? 'text' : 'name'] = name
      await createNode({ id, node_type: type, parent_id: parentId || undefined, properties: props })
      bumpViz(); setId(''); setParentId(''); setName(''); setMsg('Knoten gespeichert.')
    } catch (e: any) { setMsg(e?.response?.data?.detail ?? 'Fehler') }
  }

  const remove = async () => {
    if (!id) return
    setMsg(null)
    try { await deleteNode(id); bumpViz(); setMsg('Knoten gelöscht.') }
    catch (e: any) { setMsg(e?.response?.data?.detail ?? 'Fehler') }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ fontSize: 12, fontWeight: 700 }}>Knoten</div>
      <input style={inp} placeholder="ID (z.B. BDT_CH01_T01_C01)" value={id} onChange={(e) => setId(e.target.value)} />
      <div style={{ display: 'flex', gap: 6 }}>
        <select style={{ ...inp, flex: 1 }} value={type} onChange={(e) => setType(e.target.value as NodeType)}>
          {NODE_TYPES.map((t) => <option key={t} value={t}>{NODE_TYPE_LABELS[t]}</option>)}
        </select>
        <input style={{ ...inp, flex: 1 }} placeholder="Eltern-ID" value={parentId} onChange={(e) => setParentId(e.target.value)} />
      </div>
      <input style={inp} placeholder={type === 'Question' ? 'Fragetext' : 'Name'} value={name} onChange={(e) => setName(e.target.value)} />
      <div style={{ display: 'flex', gap: 6 }}>
        <button style={btn('#6366f1')} onClick={add}>Hinzufügen / Ändern</button>
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
