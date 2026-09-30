import { usePipelineStore } from './store/pipelineStore'
import JobSetup from './components/JobSetup'
import PipelineStepper from './components/PipelineStepper'
import ProgressLog from './components/ProgressLog'
import ExportButtons from './components/ExportButtons'
import Neo4jUploadForm from './components/Neo4jUploadForm'
import LanguageToggle from './components/LanguageToggle'
import GraphView from './components/GraphView'
import QuestionPanel from './components/QuestionPanel'
import ValidationPanel from './components/ValidationPanel'
import NextChapterPanel from './components/NextChapterPanel'
import type { JobStatus } from './types/graph'

const BANNERS: Partial<Record<JobStatus, { text: string; bg: string; color: string; spinner?: boolean }>> = {
  RUNNING: { text: 'Das Modell arbeitet… (kann 1–2 Minuten dauern — siehe Verlauf links)', bg: '#dbeafe', color: '#1e40af', spinner: true },
  AWAITING_USER_INPUT: { text: '❓ Rückfrage der KI — bitte rechts beantworten', bg: '#fef3c7', color: '#92400e' },
  AWAITING_VALIDATION: { text: '✅ Schritt fertig — Graph prüfen und rechts freigeben', bg: '#ede9fe', color: '#5b21b6' },
  AWAITING_NEXT_CHAPTER: { text: '📖 Kapitel fertig — weiteres Kapitel hinzufügen oder abschließen (rechts)', bg: '#e0f2fe', color: '#075985' },
  COMPLETED: { text: '🎉 Pipeline abgeschlossen — Cypher links exportierbar', bg: '#dcfce7', color: '#166534' },
  FAILED: { text: '⚠️ Fehler — Details links im Status', bg: '#fee2e2', color: '#991b1b' },
}

/**
 * Rotating hourglass shown while the model works.
 *
 * @returns The icon.
 */
function Hourglass() {
  return (
    <span style={{
      display: 'inline-block', animation: 'hourglassFlip 1.4s ease-in-out infinite',
      transformOrigin: '50% 50%', fontSize: 15, lineHeight: 1,
    }}>
      ⏳
    </span>
  )
}

/**
 * Banner above the graph that tells the user what to do next.
 *
 * @param status The job status.
 * @returns The banner, or null for statuses without banner.
 */
function StatusBanner({ status }: { status: JobStatus }) {
  const b = BANNERS[status]
  if (!b) return null
  return (
    <div style={{
      position: 'absolute', top: 12, left: 12,
      display: 'inline-flex', alignItems: 'center', gap: 8,
      padding: '8px 16px', borderRadius: 999, background: b.bg, color: b.color,
      fontSize: 13, fontWeight: 600, boxShadow: '0 1px 4px rgba(0,0,0,0.1)', zIndex: 10,
    }}>
      {b.spinner && <Hourglass />}
      {b.text}
    </div>
  )
}

/**
 * Three-column layout: setup and pipeline, graph, and the panel for questions, validation or the next chapter.
 *
 * @returns The application.
 */
export default function App() {
  const { job, vizReloadKey, setJob } = usePipelineStore()

  const showQuestion = job?.status === 'AWAITING_USER_INPUT' && job.pending_question
  const showValidation = job?.status === 'AWAITING_VALIDATION' || job?.status === 'COMPLETED'
  const showNextChapter = job?.status === 'AWAITING_NEXT_CHAPTER'

  return (
    <div style={{ display: 'flex', height: '100vh', fontFamily: 'system-ui, sans-serif', color: '#0f172a' }}>
      <style>{`
        @keyframes hourglassFlip {
          0%, 55%  { transform: rotate(0deg); }
          70%, 100% { transform: rotate(180deg); }
        }
      `}</style>
      {/* Left: setup / pipeline */}
      <aside style={{ width: 320, borderRight: '1px solid #e2e8f0', padding: 16, display: 'flex', flexDirection: 'column', gap: 16, overflowY: 'auto' }}>
        <div style={{ fontWeight: 800, fontSize: 18 }}>LectureToGraph</div>
        {!job ? (
          <JobSetup />
        ) : (
          <>
            <PipelineStepper job={job} />
            <LanguageToggle job={job} />
            <ProgressLog />
            <ExportButtons job={job} />
            {job.status === 'COMPLETED' && <Neo4jUploadForm job={job} />}
            <button onClick={() => setJob(null)} style={{
              marginTop: 'auto', padding: '8px 0', borderRadius: 6, cursor: 'pointer',
              border: '1px solid #e2e8f0', background: '#fff', fontSize: 12, color: '#64748b',
            }}>
              Neuer Job
            </button>
          </>
        )}
      </aside>

      {/* Center: graph */}
      <main style={{ flex: 1, position: 'relative' }}>
        {job ? (
          <>
            <GraphView jobId={job.id} reloadKey={vizReloadKey} />
            <StatusBanner status={job.status} />
          </>
        ) : (
          <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#cbd5e1', fontSize: 18 }}>
            Lade PDF(s) hoch und starte den KI-Modus
          </div>
        )}
      </main>

      {/* Right: question / validation / next chapter */}
      {job && (showQuestion || showValidation || showNextChapter) && (
        <aside style={{ width: 340, borderLeft: '1px solid #e2e8f0', padding: 16, overflowY: 'auto', background: '#fafafa' }}>
          {showQuestion
            ? <QuestionPanel jobId={job.id} payload={job.pending_question!} />
            : showNextChapter
              ? <NextChapterPanel job={job} />
              : <ValidationPanel job={job} />}
        </aside>
      )}
    </div>
  )
}
