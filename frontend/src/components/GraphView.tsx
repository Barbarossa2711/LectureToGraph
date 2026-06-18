import { useEffect, useRef, useState } from 'react'
import NeoVis, { NEOVIS_ADVANCED_CONFIG } from 'neovis.js'
import { getVizConfig } from '../api/client'
import { NODE_COLORS, NODE_SIZES, EDGE_COLORS, EDGE_TYPES } from '../types/graph'
import type { EdgeType, Stage } from '../types/graph'
import NodeInfoPopup, { type SelectedNode } from './NodeInfoPopup'

const STAGE_LAST_LABEL: Record<Stage, string> = {
  DOMAIN: 'Kapitel',
  EDGES: 'Konzept-Kanten',
  QUESTIONS: 'Wiederholungsfragen',
}

interface Props {
  jobId: string
  reloadKey: number
}

const CONTAINER_ID = 'neovis-container'

// vis-network item keys that are not Neo4j node properties
const VIS_KEYS = new Set([
  'id', 'label', 'group', 'title', 'shape', 'size', 'color', 'font', 'borderWidth',
  'image', 'x', 'y', 'raw', 'value', 'mass', 'hidden', 'physics', 'shapeProperties',
  'chosen', 'icon', 'level',
])

function extractNodeProps(item: any): Record<string, unknown> {
  if (item?.raw?.properties) return item.raw.properties
  const out: Record<string, unknown> = {}
  for (const k in item) if (!VIS_KEYS.has(k)) out[k] = item[k]
  return out
}

// The semantic concept/question edges describe meaning, not the structural
// hierarchy — they clutter the tree, so they're excluded from physics (physics:
// false) and can be hidden entirely via the toggle.
const SEMANTIC_EDGES = new Set<EdgeType>(['PREREQUISITE', 'FACILITATOR', 'SAME_AS', 'TESTS'])

// width / dashes / show-label / physics per edge type
const EDGE_STYLE: Record<EdgeType, { width: number; dashes?: boolean; label?: boolean; physics?: boolean }> = {
  HAS_CHAPTER: { width: 1 },
  HAS_TOPIC: { width: 1 },
  HAS_SUBTOPIC: { width: 1 },
  HAS_CONCEPT: { width: 1 },
  PREREQUISITE: { width: 2, label: true, physics: false },
  FACILITATOR: { width: 2, label: true, physics: false },
  SAME_AS: { width: 2, dashes: true, label: true, physics: false },
  HAS_QUESTION: { width: 1.5 },
  TESTS: { width: 2, dashes: true, label: true, physics: false },
}

function applyEdgeVisibility(net: any, hide: boolean): void {
  const ds = net?.body?.data?.edges
  if (!ds) return
  const updates = ds.get()
    .filter((e: any) => SEMANTIC_EDGES.has(e.raw?.type))
    .map((e: any) => ({ id: e.id, hidden: hide }))
  if (updates.length) ds.update(updates)
}

export default function GraphView({ jobId, reloadKey }: Props) {
  const vizRef = useRef<any>(null)
  const netRef = useRef<any>(null)
  const [selected, setSelected] = useState<SelectedNode | null>(null)
  const [hideSemantic, setHideSemantic] = useState(false)
  const hideRef = useRef(hideSemantic)
  // "only latest changes" scoped view
  const cfgRef = useRef<{ full: string; last: string | null }>({ full: '', last: null })
  const [lastOnly, setLastOnly] = useState(false)
  const lastOnlyRef = useRef(false)
  const [lastStage, setLastStage] = useState<Stage | null>(null)

  // re-apply visibility whenever the toggle flips
  useEffect(() => {
    hideRef.current = hideSemantic
    applyEdgeVisibility(netRef.current, hideSemantic)
  }, [hideSemantic])

  const toggleLastOnly = (v: boolean) => {
    setLastOnly(v)
    lastOnlyRef.current = v
    const q = v && cfgRef.current.last ? cfgRef.current.last : cfgRef.current.full
    try { vizRef.current?.renderWithCypher?.(q) } catch { /* ignore */ }
  }

  useEffect(() => {
    let cancelled = false
    setSelected(null)

    ;(async () => {
      const vc = await getVizConfig(jobId)
      if (cancelled) return

      cfgRef.current = { full: vc.initialCypher, last: vc.lastChangeCypher }
      setLastStage(vc.lastChangeCypher ? vc.lastChangeStage : null)
      const startCypher = lastOnlyRef.current && vc.lastChangeCypher
        ? vc.lastChangeCypher : vc.initialCypher

      const relationships: any = {}
      for (const t of EDGE_TYPES) {
        const st = EDGE_STYLE[t]
        relationships[t] = {
          [NEOVIS_ADVANCED_CONFIG]: {
            static: {
              color: { color: EDGE_COLORS[t], highlight: EDGE_COLORS[t], inherit: false },
              width: st.width,
              dashes: st.dashes ?? false,
              label: st.label ? t : undefined,
              font: { size: 10, color: EDGE_COLORS[t], strokeWidth: 3, strokeColor: '#fff' },
              physics: st.physics ?? true,
            },
          },
        }
      }

      const config: any = {
        containerId: CONTAINER_ID,
        neo4j: {
          serverUrl: vc.serverUrl,
          serverUser: vc.serverUser,
          serverPassword: vc.serverPassword,
        },
        visConfig: {
          nodes: {
            shape: 'dot',
            size: 16,
            borderWidth: 2,
            // node caption sits below the dot — keep it dark and readable
            font: { size: 13, color: '#1e293b', strokeWidth: 4, strokeColor: '#ffffff' },
          },
          edges: {
            arrows: { to: { enabled: true, scaleFactor: 0.6 } },
            smooth: { enabled: true, type: 'dynamic' },
          },
          groups: Object.fromEntries(
            Object.entries(NODE_COLORS).map(([label, color]) => [
              label,
              {
                color: { background: color, border: color },
                size: NODE_SIZES[label as keyof typeof NODE_SIZES],
              },
            ]),
          ),
          physics: { stabilization: { iterations: 150 } },
        },
        labels: {
          Lecture: { label: 'name' },
          Chapter: { label: 'name' },
          Topic: { label: 'name' },
          Subtopic: { label: 'name' },
          Concept: { label: 'name' },
          Question: { label: 'text' },
        },
        relationships,
        initialCypher: startCypher,
      }

      try {
        const viz = new (NeoVis as any)(config)
        vizRef.current = viz
        viz.render()

        // once the graph is drawn, wire right-click on a node -> attribute popup
        viz.registerOnEvent?.('completed', () => {
          const net = viz.network
          if (!net) return
          netRef.current = net
          applyEdgeVisibility(net, hideRef.current)
          if (net.__ctxBound) return
          net.__ctxBound = true
          net.on('oncontext', (params: any) => {
            params.event?.preventDefault?.()
            const nodeId = net.getNodeAt(params.pointer.DOM)
            if (nodeId == null) { setSelected(null); return }
            const item = net.body.data.nodes.get(nodeId)
            const props = extractNodeProps(item)
            const lbl = item?.raw?.labels?.[0] ?? item?.group ?? ''
            // pointer.DOM is relative to the graph container, which fills <main>
            // (the positioned ancestor the popup is absolutely placed against)
            setSelected({
              x: params.pointer.DOM.x,
              y: params.pointer.DOM.y,
              id: String(props.id ?? nodeId),
              label: String(lbl),
              props,
            })
          })
          net.on('click', () => setSelected(null))
          net.on('dragStart', () => setSelected(null))
        })
      } catch (err) {
        console.error('neovis render failed', err)
      }
    })()

    return () => {
      cancelled = true
      try { vizRef.current?.clearNetwork?.() } catch { /* ignore */ }
    }
  }, [jobId, reloadKey])

  return (
    <>
      <div
        id={CONTAINER_ID}
        style={{ width: '100%', height: '100%', background: '#f8fafc' }}
      />
      <div style={{
        position: 'absolute', bottom: 12, left: 12, zIndex: 20,
        display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-start',
      }}>
        {lastStage && (
          <label style={ctrl}>
            <input type="checkbox" checked={lastOnly}
              onChange={(e) => toggleLastOnly(e.target.checked)} />
            Nur letzte Änderungen ({STAGE_LAST_LABEL[lastStage]})
          </label>
        )}
        <label style={ctrl}>
          <input type="checkbox" checked={hideSemantic}
            onChange={(e) => setHideSemantic(e.target.checked)} />
          Nur Struktur (Konzept-/Fragen-Kanten ausblenden)
        </label>
      </div>
      {selected && (
        <NodeInfoPopup node={selected} onClose={() => setSelected(null)} />
      )}
    </>
  )
}

const ctrl: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer',
  background: '#fff', padding: '6px 10px', borderRadius: 999,
  border: '1px solid #e2e8f0', boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
  fontSize: 12, color: '#334155', fontWeight: 600,
}
