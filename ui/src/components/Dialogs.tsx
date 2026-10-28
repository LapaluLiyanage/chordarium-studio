import * as Dialog from '@radix-ui/react-dialog'
import { useState } from 'react'
import { useStore } from '../store'

export function PasteDialog() {
  const { dialog, setDialog, importSheet } = useStore()
  const [text, setText] = useState(''), [title, setTitle] = useState('')
  return (
    <Dialog.Root open={dialog === 'paste'} onOpenChange={(o) => !o && setDialog(null)}>
      <Dialog.Portal><Dialog.Overlay className="overlay" />
        <Dialog.Content className="dialog" style={{ position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', zIndex: 21 }}>
          <Dialog.Title>Paste chord sheet</Dialog.Title>
          <Dialog.Description className="muted">English or Sinhala. Chords over lyrics, [G]inline, or | bar | notation.</Dialog.Description>
          <input className="field" aria-label="Title" placeholder="Title (optional)" value={title} onChange={(e) => setTitle(e.target.value)} />
          <textarea aria-label="Chord sheet" value={text} onChange={(e) => setText(e.target.value)} placeholder={'Key: G\nTempo: 76\n[Chorus]\n| G | Em C | D |'} />
          <div className="row"><span className="grow" />
            <Dialog.Close asChild><button className="btn">Cancel</button></Dialog.Close>
            <button className="btn primary" disabled={!text.trim()} onClick={() => void importSheet(text, title || undefined)}>Import</button></div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

const PRESETS: { id: string; label: string }[] = [
  { id: 'rules', label: 'Rules only (no AI)' }, { id: 'ollama', label: 'Ollama (local)' }, { id: 'lmstudio', label: 'LM Studio (local)' },
  { id: 'gemini', label: 'Gemini' }, { id: 'groq', label: 'Groq' }, { id: 'openrouter', label: 'OpenRouter' }, { id: 'mistral', label: 'Mistral' },
]

export function SettingsDialog({ setup = false }: { setup?: boolean }) {
  const { dialog, setDialog, config, setConfig, testProvider, setAppearance, reducedMotion, uiScale, cubaseLink } = useStore()
  const [key, setKey] = useState(''), [result, setResult] = useState('')
  const open = dialog === (setup ? 'setup' : 'settings')
  const close = () => { if (setup) try { localStorage.setItem('chordarium.setupDone', '1') } catch { /* private mode */ } setDialog(null) }
  return (
    <Dialog.Root open={open} onOpenChange={(o) => !o && close()}>
      <Dialog.Portal><Dialog.Overlay className="overlay" />
        <Dialog.Content className="dialog" style={{ position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', zIndex: 21 }}>
          <Dialog.Title>{setup ? 'Welcome — quick setup' : 'Settings'}</Dialog.Title>
          <Dialog.Description className="muted">Pick how the assistant thinks. Rules only always works. Keys are stored in your system keyring.</Dialog.Description>
          <label>Provider<br /><select className="field" value={config?.provider ?? 'rules'} onChange={(e) => void setConfig({ provider: e.target.value })}>
            {PRESETS.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}</select></label>
          <p><label>Model<br /><input className="field" value={config?.model ?? ''} onChange={(e) => void setConfig({ model: e.target.value })} /></label></p>
          <p><label>API key<br /><input className="field" type="password" value={key} placeholder={config?.has_key ? '•••••• saved' : ''} onChange={(e) => setKey(e.target.value)} /></label>
            <button className="btn" onClick={() => { void setConfig({ api_key: key }); setKey('') }}>Save key</button></p>
          <p><button className="btn" onClick={async () => { const r = await testProvider(); setResult(r ? (r.ok ? 'Connected ✓' : r.detail) : '') }}>Test connection</button> <span role="status">{result}</span></p>
          <p className="muted">Cubase link (loopMIDI “Chordarium Remote”): {cubaseLink ? 'found' : 'not set up — optional'}</p>
          <label className="row"><input type="checkbox" checked={reducedMotion} onChange={(e) => setAppearance({ reducedMotion: e.target.checked })} /> Reduce motion</label>
          <label>UI size {uiScale}%<br /><input type="range" min={80} max={140} step={10} value={uiScale} onChange={(e) => setAppearance({ uiScale: Number(e.target.value) })} /></label>
          <div className="row"><span className="grow" /><button className="btn primary" onClick={close}>{setup ? 'Get started' : 'Done'}</button></div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
