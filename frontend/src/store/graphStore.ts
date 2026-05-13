import { create } from 'zustand'
import type { Lecture, KnowledgeNode, KnowledgeEdge } from '../types/graph'

interface GraphState {
  lectures: Lecture[]
  activeLecture: Lecture | null
  nodes: KnowledgeNode[]
  edges: KnowledgeEdge[]
  selectedNodeId: string | null

  setLectures: (lectures: Lecture[]) => void
  setActiveLecture: (lecture: Lecture | null) => void
  setGraph: (nodes: KnowledgeNode[], edges: KnowledgeEdge[]) => void
  addNode: (node: KnowledgeNode) => void
  updateNode: (id: string, properties: KnowledgeNode['properties']) => void
  removeNode: (id: string) => void
  addEdge: (edge: KnowledgeEdge) => void
  removeEdge: (sourceId: string, targetId: string, edgeType: string) => void
  setSelectedNode: (id: string | null) => void
}

export const useGraphStore = create<GraphState>((set) => ({
  lectures: [],
  activeLecture: null,
  nodes: [],
  edges: [],
  selectedNodeId: null,

  setLectures: (lectures) => set({ lectures }),
  setActiveLecture: (lecture) => set({ activeLecture: lecture, nodes: [], edges: [], selectedNodeId: null }),
  setGraph: (nodes, edges) => set({ nodes, edges }),
  addNode: (node) => set((s) => ({ nodes: [...s.nodes, node] })),
  updateNode: (id, properties) =>
    set((s) => ({
      nodes: s.nodes.map((n) => (n.id === id ? { ...n, properties: { ...n.properties, ...properties } } : n)),
    })),
  removeNode: (id) =>
    set((s) => ({
      nodes: s.nodes.filter((n) => n.id !== id),
      edges: s.edges.filter((e) => e.source_id !== id && e.target_id !== id),
    })),
  addEdge: (edge) => set((s) => ({ edges: [...s.edges, edge] })),
  removeEdge: (sourceId, targetId, edgeType) =>
    set((s) => ({
      edges: s.edges.filter(
        (e) => !(e.source_id === sourceId && e.target_id === targetId && e.edge_type === edgeType),
      ),
    })),
  setSelectedNode: (id) => set({ selectedNodeId: id }),
}))
