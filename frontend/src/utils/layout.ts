import dagre from '@dagrejs/dagre'
import type { KnowledgeNode, KnowledgeEdge } from '../types/graph'

const NODE_WIDTH = 160
const NODE_HEIGHT = 60

export function computeDagreLayout(
  knNodes: KnowledgeNode[],
  knEdges: KnowledgeEdge[],
): Record<string, { x: number; y: number }> {
  const g = new dagre.graphlib.Graph()
  g.setGraph({ rankdir: 'TB', nodesep: 60, ranksep: 100, marginx: 40, marginy: 40 })
  g.setDefaultEdgeLabel(() => ({}))

  for (const n of knNodes) {
    g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT })
  }

  for (const e of knEdges) {
    // Only structural edges influence layout (not cross-cutting ones like REQUIRES/RELATES_TO)
    if (!['REQUIRES', 'RELATES_TO', 'TESTS_UNDERSTANDING_OF'].includes(e.edge_type)) {
      g.setEdge(e.source_id, e.target_id)
    }
  }

  dagre.layout(g)

  const positions: Record<string, { x: number; y: number }> = {}
  for (const n of knNodes) {
    const node = g.node(n.id)
    if (node) {
      positions[n.id] = {
        x: node.x - NODE_WIDTH / 2,
        y: node.y - NODE_HEIGHT / 2,
      }
    } else {
      // Disconnected node — place at bottom
      positions[n.id] = { x: 80 + Math.random() * 300, y: 500 + Math.random() * 100 }
    }
  }
  return positions
}
