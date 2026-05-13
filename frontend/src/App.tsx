import { useState } from 'react'
import LectureList from './components/LectureList'
import GraphEditor from './components/GraphEditor'
import NodePanel from './components/NodePanel'
import Toolbar, { type Tool } from './components/Toolbar'
import { useGraphStore } from './store/graphStore'

export default function App() {
  const { activeLecture, selectedNodeId, setSelectedNode } = useGraphStore()
  const [activeTool, setActiveTool] = useState<Tool>('select')
  const [layoutTrigger, setLayoutTrigger] = useState(0)

  const handleNodeSelect = (id: string | null) => {
    setSelectedNode(id)
  }

  const handleToolChange = (tool: Tool) => {
    setActiveTool(tool)
    if (tool !== 'select') setSelectedNode(null)
  }

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <LectureList />

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Header */}
        <div style={{
          height: 44, borderBottom: '1px solid #e5e7eb',
          display: 'flex', alignItems: 'center', padding: '0 16px', gap: 10,
          background: '#fff', flexShrink: 0,
        }}>
          {activeLecture ? (
            <>
              <span style={{ fontWeight: 700, fontSize: 15 }}>{activeLecture.title}</span>
              <span style={{ color: '#6b7280', fontSize: 13 }}>{activeLecture.professor}</span>
              {activeLecture.semester && (
                <span style={{ color: '#9ca3af', fontSize: 12 }}>· {activeLecture.semester}</span>
              )}
            </>
          ) : (
            <span style={{ color: '#9ca3af', fontSize: 13 }}>
              Wähle eine Vorlesung aus der linken Leiste
            </span>
          )}
        </div>

        {/* Toolbar */}
        <Toolbar
          activeTool={activeTool}
          onChange={handleToolChange}
          onResetLayout={() => setLayoutTrigger((n) => n + 1)}
          disabled={!activeLecture}
        />

        {/* Canvas + side panel */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          {activeLecture ? (
            <GraphEditor
              activeTool={activeTool}
              onNodeSelect={handleNodeSelect}
              onResetLayout={() => setLayoutTrigger((n) => n + 1)}
              layoutTrigger={layoutTrigger}
            />
          ) : (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#d1d5db', fontSize: 18 }}>
              Kein Graph geladen
            </div>
          )}

          {selectedNodeId && activeTool === 'select' && (
            <NodePanel onClose={() => setSelectedNode(null)} />
          )}
        </div>
      </div>
    </div>
  )
}
