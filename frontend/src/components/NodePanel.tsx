import { useState, useEffect } from 'react'
import { useGraphStore } from '../store/graphStore'
import { updateNode as apiUpdateNode } from '../api/client'
import { NODE_COLORS, NODE_TYPE_LABELS } from '../types/graph'
import type { NodeProperties } from '../types/graph'

interface Props {
  onClose: () => void
}

export default function NodePanel({ onClose }: Props) {
  const { selectedNodeId, nodes, updateNode } = useGraphStore()
  const selectedNode = nodes.find((n) => n.id === selectedNodeId) ?? null

  const [draft, setDraft] = useState<NodeProperties>({})
  const [saved, setSaved] = useState(false)

  // Reset draft when selected node changes
  useEffect(() => {
    setDraft(selectedNode?.properties ?? {})
    setSaved(false)
  }, [selectedNodeId]) // eslint-disable-line

  if (!selectedNode) return null

  const color = NODE_COLORS[selectedNode.node_type]

  const handleSave = async () => {
    try {
      const updated = await apiUpdateNode(selectedNode.id, draft)
      updateNode(selectedNode.id, updated.properties)
      setSaved(true)
      setTimeout(() => setSaved(false), 1500)
    } catch (e) {
      console.error(e)
    }
  }

  const isQuestion = selectedNode.node_type === 'ReviewQuestion'
  const isConcept   = selectedNode.node_type === 'Concept'
  const hasOrder    = ['Chapter', 'Topic', 'Subtopic'].includes(selectedNode.node_type)

  return (
    <div style={{
      width: 280, borderLeft: '1px solid #e5e7eb',
      display: 'flex', flexDirection: 'column', background: '#f9fafb', flexShrink: 0,
    }}>
      {/* Header */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #e5e7eb', background: '#fff', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 10, height: 10, borderRadius: '50%', background: color }} />
          <span style={{ fontWeight: 700, fontSize: 14 }}>{NODE_TYPE_LABELS[selectedNode.node_type]}</span>
        </div>
        <button onClick={onClose} style={{ border: 'none', background: 'none', cursor: 'pointer', fontSize: 18, color: '#9ca3af' }}>×</button>
      </div>

      {/* Fields */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <label style={labelStyle}>{isQuestion ? 'Frage *' : 'Titel *'}</label>
        {isQuestion ? (
          <textarea
            style={{ ...inputStyle, height: 80, resize: 'vertical' }}
            value={draft.question ?? draft.title ?? ''}
            onChange={(e) => setDraft({ ...draft, question: e.target.value })}
          />
        ) : (
          <input
            style={inputStyle}
            value={draft.title ?? ''}
            onChange={(e) => setDraft({ ...draft, title: e.target.value })}
          />
        )}

        {!isQuestion && (
          <>
            <label style={labelStyle}>Beschreibung</label>
            <textarea
              style={{ ...inputStyle, height: 72, resize: 'vertical' }}
              value={draft.description ?? ''}
              onChange={(e) => setDraft({ ...draft, description: e.target.value })}
            />
          </>
        )}

        {hasOrder && (
          <>
            <label style={labelStyle}>Reihenfolge</label>
            <input
              type="number"
              style={inputStyle}
              value={draft.order ?? ''}
              onChange={(e) => setDraft({ ...draft, order: e.target.value ? Number(e.target.value) : undefined })}
            />
          </>
        )}

        {isConcept && (
          <>
            <label style={labelStyle}>Definition</label>
            <textarea style={{ ...inputStyle, height: 80, resize: 'vertical' }} value={draft.definition ?? ''} onChange={(e) => setDraft({ ...draft, definition: e.target.value })} />
            <label style={labelStyle}>Beispiele</label>
            <textarea style={{ ...inputStyle, height: 60, resize: 'vertical' }} value={draft.examples ?? ''} onChange={(e) => setDraft({ ...draft, examples: e.target.value })} />
          </>
        )}

        {isQuestion && (
          <>
            <label style={labelStyle}>Antwort</label>
            <textarea style={{ ...inputStyle, height: 80, resize: 'vertical' }} value={draft.answer ?? ''} onChange={(e) => setDraft({ ...draft, answer: e.target.value })} />
          </>
        )}

        {/* Node ID reference */}
        <div style={{ marginTop: 4, padding: '6px 8px', background: '#f3f4f6', borderRadius: 4, fontSize: 10, color: '#9ca3af', fontFamily: 'monospace', wordBreak: 'break-all' }}>
          ID: {selectedNode.id}
        </div>
      </div>

      {/* Save button */}
      <div style={{ padding: 14, borderTop: '1px solid #e5e7eb' }}>
        <button
          onClick={handleSave}
          style={{
            width: '100%', padding: '8px 0', borderRadius: 6, border: 'none',
            background: saved ? '#16a34a' : '#6366f1',
            color: '#fff', cursor: 'pointer', fontWeight: 700, fontSize: 14,
            transition: 'background 0.2s',
          }}
        >
          {saved ? '✓ Gespeichert' : 'Speichern'}
        </button>
      </div>
    </div>
  )
}

const labelStyle: React.CSSProperties = { fontSize: 12, fontWeight: 600, color: '#374151' }
const inputStyle: React.CSSProperties = { width: '100%', padding: '7px 9px', borderRadius: 5, border: '1px solid #d1d5db', fontSize: 13, background: '#fff' }
