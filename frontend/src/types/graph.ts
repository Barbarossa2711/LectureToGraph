export type NodeType =
  | 'Lecture'
  | 'Chapter'
  | 'Topic'
  | 'Subtopic'
  | 'Concept'
  | 'Question'
  | 'Slide'

export type EdgeType =
  | 'HAS_CHAPTER'
  | 'HAS_TOPIC'
  | 'HAS_SUBTOPIC'
  | 'HAS_CONCEPT'
  | 'PREREQUISITE'
  | 'FACILITATOR'
  | 'SAME_AS'
  | 'HAS_QUESTION'
  | 'TESTS'
  | 'COVERS'

export type Stage = 'DOMAIN' | 'EDGES' | 'QUESTIONS'

export type JobStatus =
  | 'CREATED'
  | 'UPLOADED'
  | 'RUNNING'
  | 'AWAITING_USER_INPUT'
  | 'AWAITING_VALIDATION'
  | 'AWAITING_NEXT_CHAPTER'
  | 'COMPLETED'
  | 'FAILED'

export interface KnowledgeNode {
  id: string
  node_type: NodeType
  properties: Record<string, unknown>
}

export interface KnowledgeEdge {
  source_id: string
  target_id: string
  edge_type: EdgeType
}

export interface GraphResponse {
  nodes: KnowledgeNode[]
  edges: KnowledgeEdge[]
}

export interface ProviderInfo {
  name: string
  label: string
  available: boolean
  models: { id: string; label: string; default: boolean }[]
  default_model: string | null
}

export type Language = 'de' | 'en'

export interface JobSummary {
  id: string
  provider: string
  model: string
  lecture_code: string | null
  language: Language
  stage: Stage
  status: JobStatus
  chapter_no: number
  last_loaded_stage: Stage | null
  pending_question: AskUserPayload | null
  artifacts: Record<string, string[]>
  error: string | null
  uploaded_pdfs: string[]
}

export interface AskUserQuestion {
  header: string
  question: string
  multiSelect?: boolean
  options?: { label: string; description?: string }[]
}

export interface AskUserPayload {
  questions: AskUserQuestion[]
}

export interface VizConfig {
  serverUrl: string
  serverUser: string
  serverPassword: string
  initialCypher: string
  lastChangeCypher: string | null
  lastChangeStage: Stage | null
  lectureCode: string | null
}

export const STAGES: { key: Stage; label: string }[] = [
  { key: 'DOMAIN', label: 'Domain-Modell + Folien' },
  { key: 'EDGES', label: 'Konzept-Kanten' },
  { key: 'QUESTIONS', label: 'Wiederholungsfragen' },
]

export const NODE_TYPE_LABELS: Record<NodeType, string> = {
  Lecture: 'Vorlesung',
  Chapter: 'Kapitel',
  Topic: 'Thema',
  Subtopic: 'Unterthema',
  Concept: 'Konzept',
  Question: 'Frage',
  Slide: 'Folie',
}

export const EDGE_TYPE_LABELS: Record<EdgeType, string> = {
  HAS_CHAPTER: 'hat Kapitel',
  HAS_TOPIC: 'hat Thema',
  HAS_SUBTOPIC: 'hat Unterthema',
  HAS_CONCEPT: 'hat Konzept',
  PREREQUISITE: 'setzt voraus',
  FACILITATOR: 'erleichtert',
  SAME_AS: 'gleich wie',
  HAS_QUESTION: 'hat Frage',
  TESTS: 'testet',
  COVERS: 'behandelt',
}

export const NODE_COLORS: Record<NodeType, string> = {
  Lecture: '#6366f1',
  Chapter: '#0ea5e9',
  Topic: '#10b981',
  Subtopic: '#f59e0b',
  Concept: '#ef4444',
  Question: '#a855f7',
  Slide: '#475569',
}

// node size decreases gently down the hierarchy; questions/slides are smallest
export const NODE_SIZES: Record<NodeType, number> = {
  Lecture: 24,
  Chapter: 21,
  Topic: 19,
  Subtopic: 17,
  Concept: 15,
  Question: 12,
  Slide: 12,
}

// distinct colour per edge type; PREREQUISITE is emphasised (see GraphView)
export const EDGE_COLORS: Record<EdgeType, string> = {
  HAS_CHAPTER: '#38bdf8',
  HAS_TOPIC: '#34d399',
  HAS_SUBTOPIC: '#fbbf24',
  HAS_CONCEPT: '#94a3b8',
  PREREQUISITE: '#dc2626',
  FACILITATOR: '#eab308',
  SAME_AS: '#14b8a6',
  HAS_QUESTION: '#c084fc',
  TESTS: '#ec4899',
  COVERS: '#0891b2',
}

export const NODE_TYPES: NodeType[] = ['Lecture', 'Chapter', 'Topic', 'Subtopic', 'Concept', 'Question', 'Slide']
export const EDGE_TYPES: EdgeType[] = [
  'HAS_CHAPTER', 'HAS_TOPIC', 'HAS_SUBTOPIC', 'HAS_CONCEPT',
  'PREREQUISITE', 'FACILITATOR', 'SAME_AS', 'HAS_QUESTION', 'TESTS', 'COVERS',
]
