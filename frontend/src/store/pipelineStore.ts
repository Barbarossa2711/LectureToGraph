import { create } from 'zustand'
import type { JobSummary, ProviderInfo } from '../types/graph'
import { getJob, getProviders, openEvents } from '../api/client'

export interface LogEntry {
  kind: 'log' | 'tool' | 'error'
  text: string
  ts: number
}

interface PipelineState {
  providers: ProviderInfo[]
  job: JobSummary | null
  log: LogEntry[]
  vizReloadKey: number

  /** Load the LLM providers for the setup form. */
  loadProviders: () => Promise<void>
  /** Replace the current job; null returns to the setup form. */
  setJob: (job: JobSummary | null) => void
  /** Reload the current job and redraw the graph when a validation gate is entered. */
  refreshJob: () => Promise<void>
  /** Subscribe to the job's event stream, replacing any previous subscription. */
  connect: (jobId: string) => void
  /** Append an entry to the progress log, which keeps about the last 200 entries. */
  pushLog: (entry: Omit<LogEntry, 'ts'>) => void
  /** Make the graph view reload. */
  bumpViz: () => void
}

let es: EventSource | null = null

export const usePipelineStore = create<PipelineState>((set, get) => ({
  providers: [],
  job: null,
  log: [],
  vizReloadKey: 0,

  loadProviders: async () => set({ providers: await getProviders() }),

  setJob: (job) => set({ job }),

  refreshJob: async () => {
    const job = get().job
    if (!job) return
    const fresh = await getJob(job.id)
    const prev = get().job
    set({ job: fresh })
    if (fresh.status === 'AWAITING_VALIDATION' && prev?.status !== 'AWAITING_VALIDATION') {
      get().bumpViz()
    }
  },

  pushLog: (entry) =>
    set((s) => ({ log: [...s.log.slice(-200), { ...entry, ts: Date.now() }] })),

  bumpViz: () => set((s) => ({ vizReloadKey: s.vizReloadKey + 1 })),

  connect: (jobId) => {
    es?.close()
    es = openEvents(jobId)
    const refresh = () => get().refreshJob()

    es.addEventListener('status', refresh)
    es.addEventListener('question', refresh)
    es.addEventListener('gate', () => { refresh(); get().bumpViz() })
    es.addEventListener('log', (e) =>
      get().pushLog({ kind: 'log', text: JSON.parse((e as MessageEvent).data).text }))
    es.addEventListener('tool', (e) => {
      const d = JSON.parse((e as MessageEvent).data)
      get().pushLog({ kind: 'tool', text: `→ ${d.name}` })
    })
    es.addEventListener('error', (e) => {
      const raw = (e as MessageEvent).data
      if (raw) get().pushLog({ kind: 'error', text: JSON.parse(raw).message ?? raw })
    })
  },
}))
