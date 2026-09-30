import { useEffect, useRef } from 'react'
import { usePipelineStore } from '../store/pipelineStore'

/**
 * Scrolling log of the agent's messages, tool calls and errors.
 *
 * @returns The log.
 */
export default function ProgressLog() {
  const log = usePipelineStore((s) => s.log)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => { endRef.current?.scrollIntoView() }, [log])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flexShrink: 0 }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: '#475569' }}>Verlauf</div>
      <div style={{
        height: 240, overflowY: 'auto', background: '#0f172a', borderRadius: 6,
        padding: 8, fontFamily: 'monospace', fontSize: 11, color: '#e2e8f0',
      }}>
        {log.length === 0 && <div style={{ color: '#64748b' }}>—</div>}
        {log.map((e, i) => (
          <div key={i} style={{
            color: e.kind === 'error' ? '#f87171' : e.kind === 'tool' ? '#7dd3fc' : '#cbd5e1',
            whiteSpace: 'pre-wrap', marginBottom: 2,
          }}>
            {e.text}
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  )
}
