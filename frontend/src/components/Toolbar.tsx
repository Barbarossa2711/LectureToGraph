export type Tool = 'select' | 'addNode' | 'delete'

interface Props {
  activeTool: Tool
  onChange: (tool: Tool) => void
  onResetLayout: () => void
  disabled: boolean
}

const TOOLS: { id: Tool; label: string; icon: string; title: string }[] = [
  { id: 'select',  label: 'Auswählen',          icon: '↖',  title: 'Knoten auswählen & verschieben' },
  { id: 'addNode', label: 'Knoten hinzufügen',   icon: '⊕',  title: 'Auf den Canvas klicken um einen Knoten zu erstellen' },
  { id: 'delete',  label: 'Löschen',             icon: '✕',  title: 'Knoten oder Kante anklicken um sie zu löschen' },
]

export default function Toolbar({ activeTool, onChange, onResetLayout, disabled }: Props) {
  return (
    <div style={{
      height: 44,
      borderBottom: '1px solid #e5e7eb',
      display: 'flex',
      alignItems: 'center',
      padding: '0 12px',
      gap: 4,
      background: '#fff',
      flexShrink: 0,
    }}>
      {TOOLS.map((tool) => (
        <button
          key={tool.id}
          title={tool.title}
          disabled={disabled}
          onClick={() => onChange(tool.id)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '5px 12px',
            borderRadius: 6,
            border: activeTool === tool.id ? '1.5px solid #6366f1' : '1.5px solid transparent',
            background: activeTool === tool.id ? '#eef2ff' : 'transparent',
            color: activeTool === tool.id ? '#6366f1' : '#374151',
            fontWeight: activeTool === tool.id ? 700 : 400,
            fontSize: 13,
            cursor: disabled ? 'not-allowed' : 'pointer',
            opacity: disabled ? 0.4 : 1,
            transition: 'all 0.12s',
          }}
        >
          <span style={{ fontSize: 15 }}>{tool.icon}</span>
          {tool.label}
        </button>
      ))}

      <div style={{ width: 1, height: 22, background: '#e5e7eb', margin: '0 8px' }} />

      <button
        title="Dagre-Layout neu berechnen"
        disabled={disabled}
        onClick={onResetLayout}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '5px 12px',
          borderRadius: 6,
          border: '1.5px solid transparent',
          background: 'transparent',
          color: '#374151',
          fontSize: 13,
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.4 : 1,
        }}
      >
        <span style={{ fontSize: 15 }}>↺</span>
        Layout zurücksetzen
      </button>

      {/* Mode hint */}
      <div style={{ flex: 1 }} />
      {activeTool === 'addNode' && (
        <span style={{ fontSize: 12, color: '#6366f1', fontStyle: 'italic' }}>
          Auf den Canvas klicken um einen Knoten zu erstellen
        </span>
      )}
      {activeTool === 'delete' && (
        <span style={{ fontSize: 12, color: '#ef4444', fontStyle: 'italic' }}>
          Knoten oder Kante anklicken um sie zu löschen
        </span>
      )}
    </div>
  )
}
