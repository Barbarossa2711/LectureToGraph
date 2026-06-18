import axios from 'axios'
import type {
  ProviderInfo, JobSummary, VizConfig, GraphResponse,
  NodeType, EdgeType, Language,
} from '../types/graph'

const http = axios.create({ baseURL: '/api' })

// ── config / providers ───────────────────────────────────────────────
export const getProviders = (): Promise<ProviderInfo[]> =>
  http.get('/config/providers').then((r) => r.data)

// ── jobs / pipeline ──────────────────────────────────────────────────
export const createJob = (provider: string, model: string, language: Language = 'de'): Promise<JobSummary> =>
  http.post('/jobs', { provider, model, language }).then((r) => r.data)

export const setLanguage = (jobId: string, language: Language): Promise<JobSummary> =>
  http.post(`/jobs/${jobId}/language`, { language }).then((r) => r.data)

export const uploadPdfs = (jobId: string, files: File[]): Promise<{ saved: string[] }> => {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  return http.post(`/jobs/${jobId}/pdfs`, form).then((r) => r.data)
}

export const startJob = (jobId: string): Promise<JobSummary> =>
  http.post(`/jobs/${jobId}/start`).then((r) => r.data)

export const getJob = (jobId: string): Promise<JobSummary> =>
  http.get(`/jobs/${jobId}`).then((r) => r.data)

export const answerQuestion = (jobId: string, answers: Record<string, unknown>): Promise<JobSummary> =>
  http.post(`/jobs/${jobId}/answer`, { answers }).then((r) => r.data)

export const approveGate = (jobId: string): Promise<JobSummary> =>
  http.post(`/jobs/${jobId}/gate/approve`).then((r) => r.data)

export const addChapter = (jobId: string): Promise<JobSummary> =>
  http.post(`/jobs/${jobId}/add-chapter`).then((r) => r.data)

export const finishJob = (jobId: string): Promise<JobSummary> =>
  http.post(`/jobs/${jobId}/finish`).then((r) => r.data)

export const rerunStage = (jobId: string, feedback?: string): Promise<JobSummary> =>
  http.post(`/jobs/${jobId}/stage/rerun`, { feedback }).then((r) => r.data)

export const getVizConfig = (jobId: string): Promise<VizConfig> =>
  http.get(`/jobs/${jobId}/viz-config`).then((r) => r.data)

export const openEvents = (jobId: string): EventSource =>
  new EventSource(`/api/jobs/${jobId}/events`)

export const artifactUrl = (jobId: string, path: string): string =>
  `/api/jobs/${jobId}/artifact?path=${encodeURIComponent(path)}`

export const fullCypherUrl = (jobId: string): string =>
  `/api/jobs/${jobId}/full-cypher`

export const saveCypher = (jobId: string): Promise<JobSummary> =>
  http.post(`/jobs/${jobId}/save-cypher`).then((r) => r.data)

export const uploadToNeo4j = (
  jobId: string,
  creds: { uri: string; user: string; password: string; database?: string },
): Promise<{ ok: boolean; constraints: number; statements: number }> =>
  http.post(`/jobs/${jobId}/upload-neo4j`, creds).then((r) => r.data)

export interface BundledAccess {
  browser_http: string
  bolt_uri: string
  user: string
  password: string
}

export const getBundledAccess = (jobId: string): Promise<BundledAccess> =>
  http.get(`/jobs/${jobId}/bundled-access`).then((r) => r.data)

export const loadBundled = (
  jobId: string,
): Promise<{ ok: boolean; constraints: number; statements: number; browser_http: string }> =>
  http.post(`/jobs/${jobId}/load-bundled`).then((r) => r.data)

// ── manual graph editing at a validation gate ────────────────────────
export const getGraph = (code: string): Promise<GraphResponse> =>
  http.get(`/lectures/${code}/graph`).then((r) => r.data)

export const createNode = (body: {
  id: string; node_type: NodeType; parent_id?: string; properties: Record<string, unknown>
}) => http.post('/nodes', body).then((r) => r.data)

export const updateNode = (id: string, properties: Record<string, unknown>) =>
  http.put(`/nodes/${id}`, { properties }).then((r) => r.data)

export const deleteNode = (id: string): Promise<void> =>
  http.delete(`/nodes/${id}`).then(() => undefined)

export const createEdge = (body: { source_id: string; target_id: string; edge_type: EdgeType }) =>
  http.post('/edges', body).then((r) => r.data)

export const deleteEdge = (sourceId: string, targetId: string, edgeType: string): Promise<void> =>
  http.delete('/edges', { params: { source_id: sourceId, target_id: targetId, edge_type: edgeType } })
    .then(() => undefined)
