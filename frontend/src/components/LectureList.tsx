import { useEffect, useState } from 'react'
import { useGraphStore } from '../store/graphStore'
import { getLectures, createLecture, deleteLecture, getGraph } from '../api/client'
import type { LectureCreate } from '../types/graph'

const panelStyle: React.CSSProperties = {
  width: 260,
  borderRight: '1px solid #e5e7eb',
  display: 'flex',
  flexDirection: 'column',
  background: '#f9fafb',
  flexShrink: 0,
}

const headerStyle: React.CSSProperties = {
  padding: '12px 16px',
  fontWeight: 700,
  fontSize: 15,
  borderBottom: '1px solid #e5e7eb',
  background: '#fff',
}

export default function LectureList() {
  const { lectures, setLectures, activeLecture, setActiveLecture, setGraph } = useGraphStore()
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState<LectureCreate>({ title: '', professor: '' })

  useEffect(() => {
    getLectures().then(setLectures)
  }, [setLectures])

  const loadGraph = async (lecture: ReturnType<typeof useGraphStore.getState>['lectures'][0]) => {
    setActiveLecture(lecture)
    const graph = await getGraph(lecture.id)
    setGraph(graph.nodes, graph.edges)
  }

  const handleCreate = async () => {
    if (!form.title || !form.professor) return
    const created = await createLecture(form)
    setLectures([...lectures, created])
    setForm({ title: '', professor: '' })
    setCreating(false)
    await loadGraph(created)
  }

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    await deleteLecture(id)
    const updated = lectures.filter((l) => l.id !== id)
    setLectures(updated)
    if (activeLecture?.id === id) setActiveLecture(null)
  }

  return (
    <div style={panelStyle}>
      <div style={headerStyle}>Vorlesungen</div>
      <div style={{ flex: 1, overflowY: 'auto', padding: 8 }}>
        {lectures.map((l) => (
          <div
            key={l.id}
            onClick={() => loadGraph(l)}
            style={{
              padding: '10px 12px',
              borderRadius: 6,
              marginBottom: 4,
              cursor: 'pointer',
              background: activeLecture?.id === l.id ? '#e0e7ff' : '#fff',
              border: `1px solid ${activeLecture?.id === l.id ? '#6366f1' : '#e5e7eb'}`,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div>
              <div style={{ fontWeight: 600, fontSize: 13 }}>{l.title}</div>
              <div style={{ color: '#6b7280', fontSize: 11 }}>{l.professor}</div>
            </div>
            <button
              onClick={(e) => handleDelete(l.id, e)}
              style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#ef4444', fontSize: 16 }}
            >
              ×
            </button>
          </div>
        ))}
      </div>
      <div style={{ padding: 12, borderTop: '1px solid #e5e7eb' }}>
        {creating ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <input
              placeholder="Titel"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              style={inputStyle}
            />
            <input
              placeholder="Professor"
              value={form.professor}
              onChange={(e) => setForm({ ...form, professor: e.target.value })}
              style={inputStyle}
            />
            <input
              placeholder="Semester (optional)"
              value={form.semester ?? ''}
              onChange={(e) => setForm({ ...form, semester: e.target.value })}
              style={inputStyle}
            />
            <div style={{ display: 'flex', gap: 6 }}>
              <button onClick={handleCreate} style={btnPrimary}>Erstellen</button>
              <button onClick={() => setCreating(false)} style={btnSecondary}>Abbrechen</button>
            </div>
          </div>
        ) : (
          <button onClick={() => setCreating(true)} style={{ ...btnPrimary, width: '100%' }}>
            + Neue Vorlesung
          </button>
        )}
      </div>
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  padding: '6px 8px',
  borderRadius: 4,
  border: '1px solid #d1d5db',
  fontSize: 13,
  width: '100%',
}

const btnPrimary: React.CSSProperties = {
  padding: '7px 12px',
  borderRadius: 4,
  border: 'none',
  background: '#6366f1',
  color: '#fff',
  cursor: 'pointer',
  fontSize: 13,
  fontWeight: 600,
}

const btnSecondary: React.CSSProperties = {
  ...btnPrimary,
  background: '#e5e7eb',
  color: '#374151',
}
