import { useEffect, useState } from 'react'
import { updateNode, deleteNode } from '../api/client'
import { usePipelineStore } from '../store/pipelineStore'
import { NODE_TYPE_LABELS, NODE_COLORS } from '../types/graph'
import type { NodeType } from '../types/graph'

export interface SelectedNode {
  x: number
  y: number
  id: string
  label: string
  props: Record<string, unknown>
}

// Properties that cannot be edited in the popup
const READONLY_KEYS = new Set(['id'])

/**
 * Popup at the right-clicked node to view, edit and delete its properties.
 *
 * @param node The selected node with its position.
 * @param onClose Called when the popup should close.
 * @returns The popup.
 */
export default function NodeInfoPopup({
  node, onClose,
}: { node: SelectedNode; onClose: () => void }) {
  const bumpViz = usePipelineStore((s) => s.bumpViz)
  const [draft, setDraft] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  useEffect(() => {
    const d: Record<string, string> = {}
    for (const [k, v] of Object.entries(node.props)) d[k] = v == null ? '' : String(v)
    setDraft(d)
    setMsg(null)
  }, [node])

  const typeLabel = NODE_TYPE_LABELS[node.label as NodeType] ?? node.label
  const color = NODE_COLORS[node.label as NodeType] ?? '#64748b'

  const save = async () => {
    setBusy(true); setMsg(null)
    try {
      const changed: Record<string, unknown> = {}
      for (const [k, v] of Object.entries(draft)) {
        if (READONLY_KEYS.has(k)) continue
        const orig = node.props[k]
        if (String(orig ?? '') === v) continue
        // Keep numbers numeric.
        changed[k] = typeof orig === 'number' && v.trim() !== '' && !isNaN(Number(v)) ? Number(v) : v
      }
      if (Object.keys(changed).length === 0) { setMsg('Keine Änderungen.'); setBusy(false); return }
      await updateNode(node.id, changed)
      bumpViz(); onClose()
    } catch (e: any) {
      setMsg(e?.response?.data?.detail ?? 'Fehler beim Speichern'); setBusy(false)
    }
  }

  const remove = async () => {
    if (!confirm(`Knoten "${node.id}" wirklich löschen?`)) return
    setBusy(true); setMsg(null)
    try { await deleteNode(node.id); bumpViz(); onClose() }
    catch (e: any) { setMsg(e?.response?.data?.detail ?? 'Fehler beim Löschen'); setBusy(false) }
  }

  // Roughly keep the popup inside the viewport.
  const left = Math.min(node.x + 12, window.innerWidth - 320)
  const top = Math.min(node.y + 12, window.innerHeight - 260)

  return (
    <div onContextMenu={(e) => e.preventDefault()} style={{
      position: 'absolute', left, top, width: 290, zIndex: 50,
      background: '#fff', borderRadius: 8, border: '1px solid #e2e8f0',
      boxShadow: '0 8px 24px rgba(0,0,0,0.18)', padding: 12,
      display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 340, overflowY: 'auto',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontWeight: 700, fontSize: 13 }}>
          <span style={{ width: 10, height: 10, borderRadius: 999, background: color }} />
          {typeLabel}
        </span>
        <button onClick={onClose} style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: 16, color: '#94a3b8' }}>×</button>
      </div>
      <div style={{ fontSize: 10.5, color: '#94a3b8', wordBreak: 'break-all' }}>{node.id}</div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {Object.keys(draft).map((k) => (
          <label key={k} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span style={{ fontSize: 10.5, color: '#64748b', fontWeight: 600 }}>{k}</span>
            <input
              value={draft[k]}
              readOnly={READONLY_KEYS.has(k)}
              onChange={(e) => setDraft((d) => ({ ...d, [k]: e.target.value }))}
              style={{
                width: '100%', padding: '5px 7px', borderRadius: 5, fontSize: 12,
                border: '1px solid #d1d5db',
                background: READONLY_KEYS.has(k) ? '#f1f5f9' : '#fff',
                color: READONLY_KEYS.has(k) ? '#94a3b8' : '#0f172a',
              }} />
          </label>
        ))}
      </div>

      {msg && <div style={{ fontSize: 11, color: '#64748b' }}>{msg}</div>}

      <div style={{ display: 'flex', gap: 6 }}>
        <button onClick={save} disabled={busy} style={btn('#6366f1')}>
          {busy ? '…' : 'Speichern'}
        </button>
        <button onClick={remove} disabled={busy} style={btn('#dc2626')}>Löschen</button>
      </div>
    </div>
  )
}

const btn = (bg: string): React.CSSProperties => ({
  flex: 1, padding: '7px 0', borderRadius: 6, border: 'none', cursor: 'pointer',
  background: bg, color: '#fff', fontSize: 12, fontWeight: 700,
})
