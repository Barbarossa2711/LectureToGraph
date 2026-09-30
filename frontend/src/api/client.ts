import axios from 'axios'
import type {
  ProviderInfo, JobSummary, VizConfig, GraphResponse,
  NodeType, EdgeType, Language,
} from '../types/graph'

const http = axios.create({ baseURL: '/api' })

/**
 * Load the LLM providers with their availability and models.
 *
 * @returns The providers.
 */
export const getProviders = (): Promise<ProviderInfo[]> =>
  http.get('/config/providers').then((r) => r.data)

/**
 * Create a job.
 *
 * @param provider The provider name.
 * @param model The model id.
 * @param language The language the agent uses with the user.
 * @returns The new job summary.
 */
export const createJob = (provider: string, model: string, language: Language = 'de'): Promise<JobSummary> =>
  http.post('/jobs', { provider, model, language }).then((r) => r.data)

/**
 * Change the language the agent uses with the user.
 *
 * @param jobId The job id.
 * @param language The new language.
 * @returns The updated job summary.
 */
export const setLanguage = (jobId: string, language: Language): Promise<JobSummary> =>
  http.post(`/jobs/${jobId}/language`, { language }).then((r) => r.data)

/**
 * Upload lecture PDFs into the job workspace.
 *
 * @param jobId The job id.
 * @param files The PDF files.
 * @returns The stored file names.
 */
export const uploadPdfs = (jobId: string, files: File[]): Promise<{ saved: string[] }> => {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  return http.post(`/jobs/${jobId}/pdfs`, form).then((r) => r.data)
}

/**
 * Start the pipeline with the first chapter.
 *
 * @param jobId The job id.
 * @returns The updated job summary.
 */
export const startJob = (jobId: string): Promise<JobSummary> =>
  http.post(`/jobs/${jobId}/start`).then((r) => r.data)

/**
 * Load the current state of a job.
 *
 * @param jobId The job id.
 * @returns The job summary.
 */
export const getJob = (jobId: string): Promise<JobSummary> =>
  http.get(`/jobs/${jobId}`).then((r) => r.data)

/**
 * Answer the agent's pending question.
 *
 * @param jobId The job id.
 * @param answers The answers keyed by question header.
 * @returns The updated job summary.
 */
export const answerQuestion = (jobId: string, answers: Record<string, unknown>): Promise<JobSummary> =>
  http.post(`/jobs/${jobId}/answer`, { answers }).then((r) => r.data)

/**
 * Approve the current stage's result.
 *
 * @param jobId The job id.
 * @returns The updated job summary.
 */
export const approveGate = (jobId: string): Promise<JobSummary> =>
  http.post(`/jobs/${jobId}/gate/approve`).then((r) => r.data)

/**
 * Start processing the next chapter.
 *
 * @param jobId The job id.
 * @returns The updated job summary.
 */
export const addChapter = (jobId: string): Promise<JobSummary> =>
  http.post(`/jobs/${jobId}/add-chapter`).then((r) => r.data)

/**
 * Complete the job instead of adding another chapter.
 *
 * @param jobId The job id.
 * @returns The updated job summary.
 */
export const finishJob = (jobId: string): Promise<JobSummary> =>
  http.post(`/jobs/${jobId}/finish`).then((r) => r.data)

/**
 * Discard the current stage's result and regenerate it.
 *
 * @param jobId The job id.
 * @param feedback Optional feedback for the new attempt.
 * @returns The updated job summary.
 */
export const rerunStage = (jobId: string, feedback?: string): Promise<JobSummary> =>
  http.post(`/jobs/${jobId}/stage/rerun`, { feedback }).then((r) => r.data)

/**
 * Load the neovis.js configuration for the graph view.
 *
 * @param jobId The job id.
 * @returns Connection data and the Cypher queries to render.
 */
export const getVizConfig = (jobId: string): Promise<VizConfig> =>
  http.get(`/jobs/${jobId}/viz-config`).then((r) => r.data)

/**
 * Open the server-sent event stream of a job.
 *
 * @param jobId The job id.
 * @returns The event source.
 */
export const openEvents = (jobId: string): EventSource =>
  new EventSource(`/api/jobs/${jobId}/events`)

/**
 * Build the download URL of a workspace file.
 *
 * @param jobId The job id.
 * @param path The workspace-relative path.
 * @returns The URL.
 */
export const artifactUrl = (jobId: string, path: string): string =>
  `/api/jobs/${jobId}/artifact?path=${encodeURIComponent(path)}`

/**
 * Build the download URL of the current graph as Cypher.
 *
 * @param jobId The job id.
 * @returns The URL.
 */
export const fullCypherUrl = (jobId: string): string =>
  `/api/jobs/${jobId}/full-cypher`

/**
 * Save the current graph, including manual edits, as .cypher file in the workspace.
 *
 * @param jobId The job id.
 * @returns The updated job summary.
 */
export const saveCypher = (jobId: string): Promise<JobSummary> =>
  http.post(`/jobs/${jobId}/save-cypher`).then((r) => r.data)

/**
 * Upload the current graph into an external Neo4j.
 *
 * @param jobId The job id.
 * @param creds Bolt URI, credentials and optional database name.
 * @returns The upload statistics.
 */
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

/**
 * Load the connection data of the bundled Neo4j.
 *
 * @param jobId The job id.
 * @returns Browser URL, bolt URI and credentials.
 */
export const getBundledAccess = (jobId: string): Promise<BundledAccess> =>
  http.get(`/jobs/${jobId}/bundled-access`).then((r) => r.data)

/**
 * Load the current graph into the bundled Neo4j again.
 *
 * @param jobId The job id.
 * @returns The load statistics and the Neo4j Browser URL.
 */
export const loadBundled = (
  jobId: string,
): Promise<{ ok: boolean; constraints: number; statements: number; browser_http: string }> =>
  http.post(`/jobs/${jobId}/load-bundled`).then((r) => r.data)

/**
 * Load the subgraph of a lecture.
 *
 * @param code The lecture code.
 * @returns The nodes and edges.
 */
export const getGraph = (code: string): Promise<GraphResponse> =>
  http.get(`/lectures/${code}/graph`).then((r) => r.data)

/**
 * Create or update a node and link it to its parent.
 *
 * @param body Id, node type, optional parent id and properties.
 * @returns The node.
 */
export const createNode = (body: {
  id: string; node_type: NodeType; parent_id?: string; properties: Record<string, unknown>
}) => http.post('/nodes', body).then((r) => r.data)

/**
 * Merge properties into a node.
 *
 * @param id The node id.
 * @param properties The properties to set.
 * @returns The updated node.
 */
export const updateNode = (id: string, properties: Record<string, unknown>) =>
  http.put(`/nodes/${id}`, { properties }).then((r) => r.data)

/**
 * Delete a node with all its edges.
 *
 * @param id The node id.
 */
export const deleteNode = (id: string): Promise<void> =>
  http.delete(`/nodes/${id}`).then(() => undefined)

/**
 * Create an edge between two nodes.
 *
 * @param body Source id, target id and edge type.
 * @returns The edge.
 */
export const createEdge = (body: { source_id: string; target_id: string; edge_type: EdgeType }) =>
  http.post('/edges', body).then((r) => r.data)

/**
 * Delete the edges of a type between two nodes.
 *
 * @param sourceId The id of the source node.
 * @param targetId The id of the target node.
 * @param edgeType The relationship type.
 */
export const deleteEdge = (sourceId: string, targetId: string, edgeType: string): Promise<void> =>
  http.delete('/edges', { params: { source_id: sourceId, target_id: targetId, edge_type: edgeType } })
    .then(() => undefined)
