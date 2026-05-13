export type NodeType =
  | 'Lecture'
  | 'Chapter'
  | 'Topic'
  | 'Subtopic'
  | 'Concept'
  | 'ReviewQuestion'

export type EdgeType =
  | 'HAS_CHAPTER'
  | 'HAS_TOPIC'
  | 'HAS_SUBTOPIC'
  | 'HAS_CONCEPT'
  | 'RELATES_TO'
  | 'REQUIRES'
  | 'HAS_REVIEW_QUESTION'
  | 'TESTS_UNDERSTANDING_OF'

export interface Lecture {
  id: string
  title: string
  professor: string
  description?: string
  semester?: string
}

export interface LectureCreate {
  title: string
  professor: string
  description?: string
  semester?: string
}

export interface NodeProperties {
  title?: string
  description?: string
  order?: number
  definition?: string
  examples?: string
  question?: string
  answer?: string
  difficulty?: string
}

export interface KnowledgeNode {
  id: string
  node_type: NodeType
  properties: NodeProperties & Record<string, unknown>
}

export interface KnowledgeEdge {
  source_id: string
  target_id: string
  edge_type: EdgeType
}

export interface NodeCreate {
  lecture_id: string
  node_type: NodeType
  properties: NodeProperties
}

export interface EdgeCreate {
  source_id: string
  target_id: string
  edge_type: EdgeType
}

export interface GraphResponse {
  nodes: KnowledgeNode[]
  edges: KnowledgeEdge[]
}

export const NODE_TYPE_LABELS: Record<NodeType, string> = {
  Lecture: 'Vorlesung',
  Chapter: 'Kapitel',
  Topic: 'Thema',
  Subtopic: 'Unterthema',
  Concept: 'Konzept',
  ReviewQuestion: 'Wiederholungsfrage',
}

export const EDGE_TYPE_LABELS: Record<EdgeType, string> = {
  HAS_CHAPTER: 'hat Kapitel',
  HAS_TOPIC: 'hat Thema',
  HAS_SUBTOPIC: 'hat Unterthema',
  HAS_CONCEPT: 'hat Konzept',
  RELATES_TO: 'verwandt mit',
  REQUIRES: 'benötigt',
  HAS_REVIEW_QUESTION: 'hat Wiederholungsfrage',
  TESTS_UNDERSTANDING_OF: 'testet Verständnis von',
}

export const NODE_COLORS: Record<NodeType, string> = {
  Lecture: '#6366f1',
  Chapter: '#2563eb',
  Topic: '#16a34a',
  Subtopic: '#84cc16',
  Concept: '#f97316',
  ReviewQuestion: '#ec4899',
}
