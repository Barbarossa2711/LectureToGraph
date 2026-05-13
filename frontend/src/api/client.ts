import axios from 'axios'
import type {
  Lecture,
  LectureCreate,
  KnowledgeNode,
  NodeCreate,
  EdgeCreate,
  KnowledgeEdge,
  GraphResponse,
  EdgeType,
} from '../types/graph'

const http = axios.create({ baseURL: '/api' })

// Lectures
export const getLectures = (): Promise<Lecture[]> =>
  http.get('/lectures').then((r) => r.data)

export const createLecture = (body: LectureCreate): Promise<Lecture> =>
  http.post('/lectures', body).then((r) => r.data)

export const updateLecture = (id: string, body: Partial<LectureCreate>): Promise<Lecture> =>
  http.put(`/lectures/${id}`, body).then((r) => r.data)

export const deleteLecture = (id: string): Promise<void> =>
  http.delete(`/lectures/${id}`).then(() => undefined)

// Graph
export const getGraph = (lectureId: string): Promise<GraphResponse> =>
  http.get(`/lectures/${lectureId}/graph`).then((r) => r.data)

// Nodes
export const createNode = (body: NodeCreate): Promise<KnowledgeNode> =>
  http.post('/nodes', body).then((r) => r.data)

export const updateNode = (
  id: string,
  properties: KnowledgeNode['properties'],
): Promise<KnowledgeNode> =>
  http.put(`/nodes/${id}`, { properties }).then((r) => r.data)

export const deleteNode = (id: string): Promise<void> =>
  http.delete(`/nodes/${id}`).then(() => undefined)

// Edges
export const createEdge = (body: EdgeCreate): Promise<KnowledgeEdge> =>
  http.post('/edges', body).then((r) => r.data)

export const deleteEdge = (
  sourceId: string,
  targetId: string,
  edgeType: EdgeType,
): Promise<void> =>
  http
    .delete('/edges', { params: { source_id: sourceId, target_id: targetId, edge_type: edgeType } })
    .then(() => undefined)
