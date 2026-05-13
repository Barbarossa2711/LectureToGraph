import { Handle, Position } from '@xyflow/react'
import { NODE_COLORS, NODE_TYPE_LABELS } from '../types/graph'
import type { NodeType } from '../types/graph'

interface KnowledgeNodeData {
  nodeType: NodeType
  label: string
}

const handleStyle: React.CSSProperties = {
  width: 10, height: 10,
  background: '#6366f1', border: '2px solid #fff', boxShadow: '0 0 0 1px #6366f1',
}

export default function KnowledgeNodeComponent({ data }: { data: KnowledgeNodeData }) {
  const color = NODE_COLORS[data.nodeType]

  return (
    <div style={{
      background: '#fff',
      border: `2px solid ${color}`,
      borderRadius: 8,
      padding: '8px 14px',
      minWidth: 140,
      textAlign: 'center',
      cursor: 'inherit',
    }}>
      <Handle type="target" position={Position.Top}    id="top"    style={handleStyle} />
      <Handle type="source" position={Position.Bottom} id="bottom" style={handleStyle} />

      <div style={{ fontSize: 9, fontWeight: 700, color, textTransform: 'uppercase', letterSpacing: 0.5 }}>
        {NODE_TYPE_LABELS[data.nodeType]}
      </div>
      <div style={{ fontSize: 13, fontWeight: 600, color: '#111', marginTop: 2 }}>
        {data.label}
      </div>
    </div>
  )
}
