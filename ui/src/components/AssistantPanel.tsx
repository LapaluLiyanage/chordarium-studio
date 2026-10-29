import { Send } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { COPY } from '../copy'
import { useStore } from '../store'

const TRY_CLAUDE = ['Arrange the whole song as a Sinhala pop ballad', 'Make the second verse simpler and softer', 'Add a build-up into the last chorus']
const QUICK = ['Softer', 'Busier bass', 'Add a fill', 'Simpler piano', 'Remove drums']

export function AssistantPanel() {
  const { chat, thinking, sendChat, activity, config } = useStore()
  const [text, setText] = useState('')
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => { end.current?.scrollIntoView?.({ block: 'end' }) }, [chat.length])
  const send = (t: string) => { if (t.trim()) { void sendChat(t); setText('') } }
  return (
    <aside className="card chat" aria-label="Assistant">
      <h2>Assistant</h2>
      {config?.provider === 'rules' && <p className="muted">{COPY.noAi}</p>}
      <div className="row" style={{ flexWrap: 'wrap' }}>{QUICK.map((q) => <button key={q} className="chip" onClick={() => send(q)}>{q}</button>)}</div>
      <div className="chat" role="log" aria-live="polite">
        {chat.map((m) => <div key={m.id} className={`msg ${m.kind}`}>{m.kind === 'tool' ? `${m.ok === false ? '✗' : '✓'} ${m.text}` : m.text}</div>)}
        {thinking && <div className="msg muted">…</div>}<div ref={end} />
      </div>
      <form className="row" onSubmit={(e) => { e.preventDefault(); send(text) }}>
        <input className="field grow" aria-label="Message" placeholder="e.g. soft piano, bass and light drums" value={text} onChange={(e) => setText(e.target.value)} />
        <button className="icon-btn" type="submit" aria-label="Send" disabled={thinking}><Send size={18} /></button>
      </form>
      {activity.length > 0 && <><h2>Try asking Claude</h2><ul className="muted">{TRY_CLAUDE.map((t) => <li key={t}>{t}</li>)}</ul></>}
      {activity.length > 0 && <><h2>Connected AI activity</h2><ul className="muted">{activity.slice(0, 6).map((a) => <li key={a.id}>{a.text}</li>)}</ul></>}
    </aside>
  )
}
