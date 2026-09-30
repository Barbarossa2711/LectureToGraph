import { useEffect, useRef, useState } from 'react'
import NeoVis, { NEOVIS_ADVANCED_CONFIG } from 'neovis.js'
import { getVizConfig } from '../api/client'
import {
  NODE_COLORS, NODE_SIZES, NODE_TYPES, NODE_TYPE_LABELS,
  EDGE_COLORS, EDGE_TYPES, EDGE_TYPE_LABELS,
} from '../types/graph'
import type { EdgeType, NodeType, Stage } from '../types/graph'
import NodeInfoPopup, { type SelectedNode } from './NodeInfoPopup'

const STAGE_LAST_LABEL: Record<Stage, string> = {
  DOMAIN: 'Kapitel + Folien',
  EDGES: 'Konzept-Kanten',
  QUESTIONS: 'Wiederholungsfragen',
}

// Node depth in the hierarchical layout. Only the lecture structure drives the
// arrangement; semantic edges such as PREREQUISITE do not (see SEMANTIC_EDGES).
const NODE_LEVELS: Record<NodeType, number> = {
  Lecture: 0, Chapter: 1, Topic: 2, Subtopic: 3, Concept: 4, Question: 5, Slide: 6,
}

const CHAPTER_RE = /^([A-Za-z0-9]+_CH\d+)/

interface Props {
  jobId: string
  reloadKey: number
}

const CONTAINER_ID = 'neovis-container'

// vis-network item keys that are no Neo4j node properties
const VIS_KEYS = new Set([
  'id', 'label', 'group', 'title', 'shape', 'size', 'color', 'font', 'borderWidth',
  'image', 'x', 'y', 'raw', 'value', 'mass', 'hidden', 'physics', 'shapeProperties',
  'chosen', 'icon', 'level',
])

/**
 * Read the Neo4j properties of a vis-network node.
 *
 * @param item The vis-network node.
 * @returns The node properties.
 */
function extractNodeProps(item: any): Record<string, unknown> {
  if (item?.raw?.properties) return item.raw.properties
  const out: Record<string, unknown> = {}
  for (const k in item) if (!VIS_KEYS.has(k)) out[k] = item[k]
  return out
}

/**
 * Read the Neo4j label of a vis-network node.
 *
 * @param item The vis-network node.
 * @returns The first label, or '' if unknown.
 */
function nodeLabelOf(item: any): string {
  return item?.raw?.labels?.[0] ?? item?.group ?? ''
}

/**
 * Read the Neo4j id of a vis-network node.
 *
 * @param item The vis-network node.
 * @returns The id property, or the vis-network id as fallback.
 */
function nodeIdOf(item: any): string {
  return String(item?.raw?.properties?.id ?? item?.id ?? '')
}

/**
 * Extract the chapter prefix <CODE>_CHNN from a node id.
 *
 * @param id The node id.
 * @returns The prefix, or null if the id has none.
 */
function chapterPrefixOf(id: string): string | null {
  const m = CHAPTER_RE.exec(id)
  return m ? m[1] : null
}

// Semantic edges describe meaning, not the hierarchy. They are excluded from the
// physics simulation so they do not distort the tree layout.
const SEMANTIC_EDGES = new Set<EdgeType>(['PREREQUISITE', 'FACILITATOR', 'SAME_AS', 'TESTS', 'COVERS'])

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
  COVERS: { width: 1, dashes: true },
}

/**
 * Hide the nodes of the filtered types and chapters and show all others.
 *
 * @param net The vis-network instance.
 * @param hiddenTypes The hidden node labels.
 * @param hiddenChapters The hidden chapter prefixes.
 */
function applyNodeVisibility(net: any, hiddenTypes: Set<string>, hiddenChapters: Set<string>): void {
  const ds = net?.body?.data?.nodes
  if (!ds) return
  const updates = ds.get().map((nd: any) => {
    const cp = chapterPrefixOf(nodeIdOf(nd))
    const hidden = hiddenTypes.has(nodeLabelOf(nd)) || (cp != null && hiddenChapters.has(cp))
    return { id: nd.id, hidden }
  })
  if (updates.length) ds.update(updates)
}

/**
 * Hide the edges of the filtered types and show all others.
 *
 * @param net The vis-network instance.
 * @param hidden The hidden relationship types.
 */
function applyEdgeVisibility(net: any, hidden: Set<string>): void {
  const ds = net?.body?.data?.edges
  if (!ds) return
  const updates = ds.get().map((e: any) => ({ id: e.id, hidden: hidden.has(e.raw?.type) }))
  if (updates.length) ds.update(updates)
}

/**
 * Renders the lecture graph from Neo4j with neovis.js, with filters, layout switch and a
 * right-click popup to edit nodes.
 *
 * @param jobId The job id.
 * @param reloadKey Changing this value redraws the graph.
 * @returns The graph view.
 */
export default function GraphView({ jobId, reloadKey }: Props) {
  const vizRef = useRef<any>(null)
  const netRef = useRef<any>(null)
  const [selected, setSelected] = useState<SelectedNode | null>(null)

  // Visibility filters: a key in a set is hidden.
  const [hiddenNodes, setHiddenNodes] = useState<Set<string>>(new Set())
  const [hiddenEdges, setHiddenEdges] = useState<Set<string>>(new Set())
  const [hiddenChapters, setHiddenChapters] = useState<Set<string>>(new Set())
  const hiddenNodesRef = useRef(hiddenNodes)
  const hiddenEdgesRef = useRef(hiddenEdges)
  const hiddenChaptersRef = useRef(hiddenChapters)
  const [chapters, setChapters] = useState<{ id: string; name: string; index: number }[]>([])
  const [filterOpen, setFilterOpen] = useState(false)

  const [hierarchical, setHierarchical] = useState(false)

  // "Only latest changes" view
  const cfgRef = useRef<{ full: string; last: string | null }>({ full: '', last: null })
  const [lastOnly, setLastOnly] = useState(false)
  const lastOnlyRef = useRef(false)
  const [lastStage, setLastStage] = useState<Stage | null>(null)

  useEffect(() => {
    hiddenNodesRef.current = hiddenNodes
    applyNodeVisibility(netRef.current, hiddenNodes, hiddenChaptersRef.current)
  }, [hiddenNodes])
  useEffect(() => {
    hiddenChaptersRef.current = hiddenChapters
    applyNodeVisibility(netRef.current, hiddenNodesRef.current, hiddenChapters)
  }, [hiddenChapters])
  useEffect(() => {
    hiddenEdgesRef.current = hiddenEdges
    applyEdgeVisibility(netRef.current, hiddenEdges)
  }, [hiddenEdges])

  const toggleInSet = (setter: typeof setHiddenNodes, t: string) =>
    setter((prev) => {
      const n = new Set(prev)
      if (n.has(t)) n.delete(t); else n.add(t)
      return n
    })
  const toggleNodeType = (t: string) => toggleInSet(setHiddenNodes, t)
  const toggleEdgeType = (t: string) => toggleInSet(setHiddenEdges, t)
  const toggleChapter = (id: string) => toggleInSet(setHiddenChapters, id)

  const hideAllSemantic = () => setHiddenEdges(new Set<string>(SEMANTIC_EDGES))
  const resetFilters = () => {
    setHiddenNodes(new Set())
    setHiddenEdges(new Set())
    setHiddenChapters(new Set())
  }

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

      const groups = Object.fromEntries(
        NODE_TYPES.map((label) => [
          label,
          {
            color: { background: NODE_COLORS[label], border: NODE_COLORS[label] },
            size: NODE_SIZES[label],
            ...(hierarchical ? { level: NODE_LEVELS[label] } : {}),
          },
        ]),
      )

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
            font: { size: 13, color: '#1e293b', strokeWidth: 4, strokeColor: '#ffffff' },
          },
          edges: {
            arrows: { to: { enabled: true, scaleFactor: 0.6 } },
            smooth: hierarchical
              ? { enabled: true, type: 'cubicBezier', forceDirection: 'vertical', roundness: 0.4 }
              : { enabled: true, type: 'dynamic' },
          },
          groups,
          // In the hierarchical layout the levels arrange the nodes; physics is off
          // so semantic edges do not move them.
          physics: hierarchical ? { enabled: false } : { stabilization: { iterations: 150 } },
          layout: hierarchical
            ? {
                hierarchical: {
                  enabled: true, direction: 'UD', sortMethod: 'directed',
                  levelSeparation: 120, nodeSpacing: 80, treeSpacing: 110,
                  blockShifting: true, edgeMinimization: true, parentCentralization: true,
                },
              }
            : { hierarchical: { enabled: false } },
        },
        labels: {
          Lecture: { label: 'name' },
          Chapter: { label: 'name' },
          Topic: { label: 'name' },
          Subtopic: { label: 'name' },
          Concept: { label: 'name' },
          Question: { label: 'text' },
          Slide: { label: 'title' },
        },
        relationships,
        initialCypher: startCypher,
      }

      try {
        const viz = new (NeoVis as any)(config)
        vizRef.current = viz
        viz.render()

        // After each draw: re-apply filters, collect chapters, bind the right-click popup.
        viz.registerOnEvent?.('completed', () => {
          const net = viz.network
          if (!net) return
          netRef.current = net
          applyNodeVisibility(net, hiddenNodesRef.current, hiddenChaptersRef.current)
          applyEdgeVisibility(net, hiddenEdgesRef.current)

          const chs: { id: string; name: string; index: number }[] = []
          for (const nd of net.body.data.nodes.get()) {
            if (nodeLabelOf(nd) !== 'Chapter') continue
            const props: any = nd.raw?.properties ?? {}
            chs.push({
              id: String(props.id ?? ''),
              name: String(props.name ?? props.id ?? ''),
              index: Number(props.index ?? 0),
            })
          }
          chs.sort((a, b) => a.index - b.index)
          setChapters(chs)

          if (net.__ctxBound) return
          net.__ctxBound = true
          net.on('oncontext', (params: any) => {
            params.event?.preventDefault?.()
            const nodeId = net.getNodeAt(params.pointer.DOM)
            if (nodeId == null) { setSelected(null); return }
            const item = net.body.data.nodes.get(nodeId)
            const props = extractNodeProps(item)
            const lbl = nodeLabelOf(item)
            // pointer.DOM is relative to the graph container, which fills <main>,
            // the positioned ancestor of the popup.
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
  }, [jobId, reloadKey, hierarchical])

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
        {filterOpen && (
          <div style={panel}>
            <div style={panelHead}>
              <span>Ansicht filtern</span>
              <div style={{ display: 'flex', gap: 6 }}>
                <button style={miniBtn} onClick={resetFilters}>Zurücksetzen</button>
                <button style={miniBtn} onClick={hideAllSemantic}>Nur Struktur</button>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 16 }}>
              <div>
                <div style={colHead}>Knoten</div>
                {NODE_TYPES.map((t: NodeType) => (
                  <label key={t} style={row}>
                    <input type="checkbox" checked={!hiddenNodes.has(t)}
                      onChange={() => toggleNodeType(t)} />
                    <span style={{ ...dot, background: NODE_COLORS[t] }} />
                    {NODE_TYPE_LABELS[t]}
                  </label>
                ))}
              </div>
              <div>
                <div style={colHead}>Kanten</div>
                {EDGE_TYPES.map((t: EdgeType) => (
                  <label key={t} style={row}>
                    <input type="checkbox" checked={!hiddenEdges.has(t)}
                      onChange={() => toggleEdgeType(t)} />
                    <span style={{ ...dot, background: EDGE_COLORS[t] }} />
                    {EDGE_TYPE_LABELS[t]}
                  </label>
                ))}
              </div>
            </div>
            {chapters.length > 1 && (
              <div style={{ marginTop: 10 }}>
                <div style={colHead}>Kapitel</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '2px 14px' }}>
                  {chapters.map((c) => (
                    <label key={c.id} style={row}>
                      <input type="checkbox" checked={!hiddenChapters.has(c.id)}
                        onChange={() => toggleChapter(c.id)} />
                      {c.index ? `${c.index}. ` : ''}{c.name}
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        {lastStage && (
          <label style={ctrl}>
            <input type="checkbox" checked={lastOnly}
              onChange={(e) => toggleLastOnly(e.target.checked)} />
            Nur letzte Änderungen ({STAGE_LAST_LABEL[lastStage]})
          </label>
        )}
        <label style={ctrl}>
          <input type="checkbox" checked={hierarchical}
            onChange={(e) => setHierarchical(e.target.checked)} />
          Hierarchisches Layout
        </label>
        <button style={{ ...ctrl, cursor: 'pointer' }} onClick={() => setFilterOpen((o) => !o)}>
          🔍 Filter {filterOpen ? '▾' : '▸'}
          {(hiddenNodes.size + hiddenEdges.size + hiddenChapters.size) > 0 &&
            ` · ${hiddenNodes.size + hiddenEdges.size + hiddenChapters.size} ausgeblendet`}
        </button>
      </div>
      {selected && (
        <NodeInfoPopup node={selected} onClose={() => setSelected(null)} />
      )}
    </>
  )
}

const ctrl: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 6,
  background: '#fff', padding: '6px 10px', borderRadius: 999,
  border: '1px solid #e2e8f0', boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
  fontSize: 12, color: '#334155', fontWeight: 600,
}

const panel: React.CSSProperties = {
  background: '#fff', padding: '10px 12px', borderRadius: 10,
  border: '1px solid #e2e8f0', boxShadow: '0 2px 10px rgba(0,0,0,0.12)',
  fontSize: 12, color: '#334155', maxHeight: '60vh', overflowY: 'auto',
}

const panelHead: React.CSSProperties = {
  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  gap: 12, fontWeight: 700, marginBottom: 8,
}

const colHead: React.CSSProperties = {
  fontWeight: 700, fontSize: 11, color: '#64748b',
  textTransform: 'uppercase', letterSpacing: 0.4, marginBottom: 4,
}

const row: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer',
  padding: '2px 0', whiteSpace: 'nowrap',
}

const dot: React.CSSProperties = {
  width: 10, height: 10, borderRadius: 3, display: 'inline-block', flexShrink: 0,
}

const miniBtn: React.CSSProperties = {
  cursor: 'pointer', fontSize: 11, fontWeight: 600, color: '#475569',
  background: '#f1f5f9', border: '1px solid #e2e8f0', borderRadius: 6, padding: '2px 8px',
}
