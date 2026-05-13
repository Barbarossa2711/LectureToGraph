import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Connection,
  type Node,
  type Edge,
  MarkerType,
  ConnectionMode,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useGraphStore } from '../store/graphStore'
import { createEdge as apiCreateEdge, deleteEdge as apiDeleteEdge, createNode, deleteNode as apiDeleteNode } from '../api/client'
import { NODE_COLORS, NODE_TYPE_LABELS, EDGE_TYPE_LABELS } from '../types/graph'
import type { KnowledgeNode, EdgeType, NodeType, NodeProperties } from '../types/graph'
import { computeDagreLayout } from '../utils/layout'
import KnowledgeNodeComponent from './KnowledgeNodeComponent'
import type { Tool } from './Toolbar'

// ── Smart edge defaults ───────────────────────────────────────────────────────
const SMART_DEFAULTS: Partial<Record<string, EdgeType>> = {
  'Lecture-Chapter':         'HAS_CHAPTER',
  'Chapter-Topic':           'HAS_TOPIC',
  'Chapter-ReviewQuestion':  'HAS_REVIEW_QUESTION',
  'Topic-Subtopic':          'HAS_SUBTOPIC',
  'Topic-Concept':           'HAS_CONCEPT',
  'Topic-ReviewQuestion':    'HAS_REVIEW_QUESTION',
  'Subtopic-Concept':        'HAS_CONCEPT',
  'ReviewQuestion-Concept':  'TESTS_UNDERSTANDING_OF',
  'ReviewQuestion-Topic':    'TESTS_UNDERSTANDING_OF',
}
function smartDefault(src?: NodeType, tgt?: NodeType): EdgeType {
  if (!src || !tgt) return 'RELATES_TO'
  return SMART_DEFAULTS[`${src}-${tgt}`] ?? 'REQUIRES'
}

const ALL_EDGE_TYPES: EdgeType[] = [
  'HAS_CHAPTER', 'HAS_TOPIC', 'HAS_SUBTOPIC', 'HAS_CONCEPT',
  'HAS_REVIEW_QUESTION', 'REQUIRES', 'RELATES_TO', 'TESTS_UNDERSTANDING_OF',
]

const ALL_NODE_TYPES = Object.keys(NODE_TYPE_LABELS).filter((t) => t !== 'Lecture') as NodeType[]

const NODE_TYPES = { knowledge: KnowledgeNodeComponent }

// ── Builders ──────────────────────────────────────────────────────────────────
function buildFlowNode(n: KnowledgeNode, position: { x: number; y: number }): Node {
  return {
    id: n.id,
    type: 'knowledge',
    position,
    data: { nodeType: n.node_type, label: n.properties.title ?? n.id },
  }
}

function buildFlowEdge(e: { source_id: string; target_id: string; edge_type: EdgeType }): Edge {
  return {
    id: `${e.source_id}__${e.edge_type}__${e.target_id}`,
    source: e.source_id,
    target: e.target_id,
    label: EDGE_TYPE_LABELS[e.edge_type],
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { strokeWidth: 1.5 },
    labelStyle: { fontSize: 10 },
    labelBgStyle: { fill: '#f9fafb', fillOpacity: 0.9 },
  }
}

// ── Component ─────────────────────────────────────────────────────────────────
interface Props {
  activeTool: Tool
  onNodeSelect: (id: string | null) => void
  onResetLayout: () => void
  layoutTrigger: number
}

export default function GraphEditor({ activeTool, onNodeSelect, onResetLayout, layoutTrigger }: Props) {
  const {
    nodes: knNodes, edges: knEdges,
    activeLecture,
    addNode: storeAddNode, addEdge: storeAddEdge,
    removeNode: storeRemoveNode, removeEdge,
  } = useGraphStore()

  const positions = useRef<Record<string, { x: number; y: number }>>({})
  const layoutAppliedFor = useRef('')

  // New-connection dialog
  const [pendingConn, setPendingConn] = useState<{
    conn: Connection
    defaultType: EdgeType
  } | null>(null)
  const [connEdgeType, setConnEdgeType] = useState<EdgeType>('RELATES_TO')

  // Edge-edit dialog
  const [editingEdge, setEditingEdge] = useState<{ edge: Edge; type: EdgeType } | null>(null)

  // Add-node dialog (triggered by pane click in addNode mode)
  const [showAddNode, setShowAddNode] = useState(false)
  const [newNodeType, setNewNodeType] = useState<NodeType>('Chapter')
  const [newNodeProps, setNewNodeProps] = useState<NodeProperties>({})

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])

  const applyLayout = useCallback((targetNodes = knNodes, targetEdges = knEdges) => {
    const computed = computeDagreLayout(targetNodes, targetEdges)
    Object.assign(positions.current, computed)
    setNodes(targetNodes.map((n) => buildFlowNode(n, positions.current[n.id])))
  }, [knNodes, knEdges, setNodes])

  // External layout-reset trigger from toolbar
  useEffect(() => { if (layoutTrigger > 0) applyLayout() }, [layoutTrigger]) // eslint-disable-line

  useEffect(() => {
    const key = knNodes.map((n) => n.id).sort().join(',')
    if (key !== layoutAppliedFor.current) {
      layoutAppliedFor.current = key
      applyLayout(knNodes, knEdges)
    } else {
      setNodes(knNodes.map((n) => buildFlowNode(n, positions.current[n.id] ?? { x: 0, y: 0 })))
    }
  }, [knNodes]) // eslint-disable-line

  useEffect(() => { setEdges(knEdges.map(buildFlowEdge)) }, [knEdges, setEdges])

  const onNodesChangeWrapped: typeof onNodesChange = useCallback((changes) => {
    onNodesChange(changes)
    for (const c of changes) {
      if (c.type === 'position' && c.position) positions.current[c.id] = c.position
    }
  }, [onNodesChange])

  const nodeTypeMap = useMemo(
    () => Object.fromEntries(knNodes.map((n) => [n.id, n.node_type])),
    [knNodes],
  )

  const onConnect = useCallback((conn: Connection) => {
    const defaultType = smartDefault(nodeTypeMap[conn.source], nodeTypeMap[conn.target])
    setPendingConn({ conn, defaultType })
    setConnEdgeType(defaultType)
  }, [nodeTypeMap])

  const confirmConnection = useCallback(async () => {
    if (!pendingConn) return
    try {
      const created = await apiCreateEdge({
        source_id: pendingConn.conn.source,
        target_id: pendingConn.conn.target,
        edge_type: connEdgeType,
      })
      storeAddEdge(created)
    } catch (e) { console.error(e) }
    finally { setPendingConn(null) }
  }, [pendingConn, connEdgeType, storeAddEdge])

  // Node click — behaviour depends on active tool
  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    if (activeTool === 'delete') {
      if (!confirm(`Knoten "${(node.data as { label: string }).label}" und alle zugehörigen Kanten löschen?`)) return
      apiDeleteNode(node.id)
        .then(() => storeRemoveNode(node.id))
        .catch(console.error)
    } else {
      onNodeSelect(node.id)
    }
  }, [activeTool, onNodeSelect, storeRemoveNode])

  // Edge click — delete mode or edit dialog
  const onEdgeClick = useCallback((_: React.MouseEvent, edge: Edge) => {
    const edgeType = edge.id.split('__')[1] as EdgeType
    if (activeTool === 'delete') {
      if (!confirm(`Kante "${EDGE_TYPE_LABELS[edgeType]}" löschen?`)) return
      apiDeleteEdge(edge.source, edge.target, edgeType)
        .then(() => removeEdge(edge.source, edge.target, edgeType))
        .catch(console.error)
    } else {
      setEditingEdge({ edge, type: edgeType })
    }
  }, [activeTool, removeEdge])

  // Canvas click in addNode mode
  const onPaneClick = useCallback(() => {
    if (activeTool !== 'addNode') return
    setNewNodeType('Chapter')
    setNewNodeProps({})
    setShowAddNode(true)
  }, [activeTool])

  const confirmAddNode = useCallback(async () => {
    if (!activeLecture || !newNodeProps.title) return
    try {
      const node = await createNode({ lecture_id: activeLecture.id, node_type: newNodeType, properties: newNodeProps })
      storeAddNode(node)
      if (newNodeType === 'Chapter') {
        storeAddEdge({ source_id: activeLecture.id, target_id: node.id, edge_type: 'HAS_CHAPTER' })
      }
    } catch (e) { console.error(e) }
    finally { setShowAddNode(false); setNewNodeProps({}) }
  }, [activeLecture, newNodeType, newNodeProps, storeAddNode, storeAddEdge])

  const saveEditedEdge = useCallback(async () => {
    if (!editingEdge) return
    const oldType = editingEdge.edge.id.split('__')[1] as EdgeType
    try {
      await apiDeleteEdge(editingEdge.edge.source, editingEdge.edge.target, oldType)
      removeEdge(editingEdge.edge.source, editingEdge.edge.target, oldType)
      const created = await apiCreateEdge({ source_id: editingEdge.edge.source, target_id: editingEdge.edge.target, edge_type: editingEdge.type })
      storeAddEdge(created)
    } catch (e) { console.error(e) }
    finally { setEditingEdge(null) }
  }, [editingEdge, removeEdge, storeAddEdge])

  const deleteEditedEdge = useCallback(async () => {
    if (!editingEdge) return
    const edgeType = editingEdge.edge.id.split('__')[1] as EdgeType
    try {
      await apiDeleteEdge(editingEdge.edge.source, editingEdge.edge.target, edgeType)
      removeEdge(editingEdge.edge.source, editingEdge.edge.target, edgeType)
    } catch (e) { console.error(e) }
    finally { setEditingEdge(null) }
  }, [editingEdge, removeEdge])

  const cursorStyle = activeTool === 'addNode' ? 'crosshair' : activeTool === 'delete' ? 'not-allowed' : 'default'

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative', cursor: cursorStyle }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        onNodesChange={onNodesChangeWrapped}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onEdgeClick={onEdgeClick}
        onPaneClick={onPaneClick}
        isValidConnection={(c) => c.source !== c.target}
        connectionMode={ConnectionMode.Loose}
        nodesDraggable={activeTool === 'select'}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap
          nodeColor={(node) => NODE_COLORS[(node.data as { nodeType: NodeType }).nodeType] ?? '#999'}
          style={{ border: '1px solid #e5e7eb' }}
        />
      </ReactFlow>

      {/* Add-node dialog */}
      {showAddNode && (
        <Overlay>
          <DialogBox title="Knoten erstellen">
            <select value={newNodeType} onChange={(e) => setNewNodeType(e.target.value as NodeType)} style={selectStyle}>
              {ALL_NODE_TYPES.map((t) => <option key={t} value={t}>{NODE_TYPE_LABELS[t]}</option>)}
            </select>
            <input
              autoFocus
              placeholder="Titel *"
              value={newNodeProps.title ?? ''}
              onChange={(e) => setNewNodeProps({ ...newNodeProps, title: e.target.value })}
              style={inputStyle}
              onKeyDown={(e) => e.key === 'Enter' && confirmAddNode()}
            />
            <input
              placeholder="Beschreibung (optional)"
              value={newNodeProps.description ?? ''}
              onChange={(e) => setNewNodeProps({ ...newNodeProps, description: e.target.value })}
              style={inputStyle}
            />
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={confirmAddNode} disabled={!newNodeProps.title} style={btnPrimary}>Erstellen</button>
              <button onClick={() => setShowAddNode(false)} style={btnSecondary}>Abbrechen</button>
            </div>
          </DialogBox>
        </Overlay>
      )}

      {/* New-connection dialog */}
      {pendingConn && (
        <Overlay>
          <DialogBox title="Kantentyp auswählen">
            <select value={connEdgeType} onChange={(e) => setConnEdgeType(e.target.value as EdgeType)} style={selectStyle}>
              {ALL_EDGE_TYPES.map((t) => <option key={t} value={t}>{EDGE_TYPE_LABELS[t]}  ({t})</option>)}
            </select>
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={confirmConnection} style={btnPrimary}>Verbinden</button>
              <button onClick={() => setPendingConn(null)} style={btnSecondary}>Abbrechen</button>
            </div>
          </DialogBox>
        </Overlay>
      )}

      {/* Edge-edit dialog */}
      {editingEdge && (
        <Overlay>
          <DialogBox title="Kante bearbeiten">
            <select value={editingEdge.type} onChange={(e) => setEditingEdge({ ...editingEdge, type: e.target.value as EdgeType })} style={selectStyle}>
              {ALL_EDGE_TYPES.map((t) => <option key={t} value={t}>{EDGE_TYPE_LABELS[t]}  ({t})</option>)}
            </select>
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={saveEditedEdge} style={btnPrimary}>Speichern</button>
              <button onClick={deleteEditedEdge} style={{ ...btnPrimary, background: '#ef4444' }}>Löschen</button>
              <button onClick={() => setEditingEdge(null)} style={btnSecondary}>Abbrechen</button>
            </div>
          </DialogBox>
        </Overlay>
      )}
    </div>
  )
}

function Overlay({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10 }}>
      {children}
    </div>
  )
}

function DialogBox({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: '#fff', borderRadius: 10, padding: 24, minWidth: 320, boxShadow: '0 8px 32px rgba(0,0,0,0.18)', display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ fontWeight: 700, fontSize: 15 }}>{title}</div>
      {children}
    </div>
  )
}

const selectStyle: React.CSSProperties = { width: '100%', padding: '8px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 14 }
const inputStyle: React.CSSProperties = { width: '100%', padding: '8px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 14 }
const btnPrimary: React.CSSProperties = { flex: 1, padding: '8px 0', borderRadius: 6, border: 'none', background: '#6366f1', color: '#fff', cursor: 'pointer', fontWeight: 700, fontSize: 14 }
const btnSecondary: React.CSSProperties = { ...btnPrimary, background: '#e5e7eb', color: '#374151' }
