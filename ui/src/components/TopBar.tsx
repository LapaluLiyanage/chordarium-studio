import { Redo2, Settings, Undo2 } from 'lucide-react'
import { KEYS, TIME_SIGNATURES } from '../chords'
import { useStore } from '../store'
import { BrandLogo } from './BrandLogo'
import { StatusChip } from './StatusChip'

export function TopBar() {
  const { snap, setMeta, undo, redo, setDialog, saved, view, setView } = useStore()
  const song = snap?.song
  return (
    <header className="topbar">
      <BrandLogo /><strong>Chordarium Studio</strong>
      {song && (
        <>
          <span className="muted">{song.title}</span>
          <label className="row">Key
            <select className="field" aria-label="Key" value={song.key ?? ''} onChange={(e) => void setMeta({ key: e.target.value })}>
              {!song.key && <option value="">—</option>}{KEYS.map((k) => <option key={k}>{k}</option>)}
            </select>
          </label>
          <label className="row">BPM
            <input className="field" aria-label="Tempo" type="number" min={30} max={300} style={{ width: 64 }} defaultValue={song.tempo_bpm} key={song.tempo_bpm}
              onBlur={(e) => { const v = Number(e.target.value); if (v >= 30 && v <= 300 && v !== song.tempo_bpm) void setMeta({ tempo_bpm: v }) }} />
          </label>
          <select className="field" aria-label="Time signature" value={song.time_signature.join('/')}
            onChange={(e) => void setMeta({ time_signature: e.target.value.split('/').map(Number) })}>
            {TIME_SIGNATURES.map((t) => <option key={t.join('/')}>{t.join('/')}</option>)}
          </select>
        </>
      )}
      <span className="grow" />
      <span className="muted" aria-live="polite">{saved ? 'Saved' : 'Saving…'}</span>
      <StatusChip />
      <button className="icon-btn" aria-label="Undo" onClick={() => void undo()}><Undo2 size={18} /></button>
      <button className="icon-btn" aria-label="Redo" onClick={() => void redo()}><Redo2 size={18} /></button>
      <button className="btn" onClick={() => setView(view === 'live' ? 'arranger' : 'live')}>{view === 'live' ? 'Arranger' : 'Live chord'}</button>
      <button className="icon-btn" aria-label="Settings" onClick={() => setDialog('settings')}><Settings size={18} /></button>
    </header>
  )
}
