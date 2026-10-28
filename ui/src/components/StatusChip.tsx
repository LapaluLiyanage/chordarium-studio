import { useStore } from '../store'

export function StatusChip() {
  const conn = useStore((s) => s.conn)
  const provider = useStore((s) => s.config?.provider ?? 'rules')
  const link = useStore((s) => s.cubaseLink)
  const tone = conn === 'ready' ? 'ok' : conn === 'down' ? 'bad' : 'warn'
  return (
    <span className="row" role="status">
      <span className="chip"><span className={`dot ${tone}`} />{conn === 'ready' ? 'Engine ready' : conn === 'down' ? 'Engine offline' : 'Starting…'}</span>
      <span className="chip">AI: {provider === 'rules' ? 'rules only' : provider}</span>
      <span className="chip"><span className={`dot ${link ? 'ok' : ''}`} />Cubase {link ? 'linked' : 'not linked'}</span>
    </span>
  )
}
