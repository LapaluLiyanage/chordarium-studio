import { Redo2, Settings, Undo2, ZoomIn, ZoomOut } from 'lucide-react'
import { KEYS, TIME_SIGNATURES } from '../chords'
import { useStore } from '../store'
import { BrandLogo } from './BrandLogo'
import { StatusChip } from './StatusChip'

export function TopBar() {
  const { snap, setMeta, undo, redo, setDialog, saved, view, setView, uiScale, setAppearance } = useStore()
  const resize = (delta: number) => setAppearance({ uiScale: Math.min(160, Math.max(70, uiScale + delta)) })
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
      <span className="seg" role="group" aria-label="View">
        <button aria-pressed={view === 'arranger'} onClick={() => setView('arranger')}>Arranger</button>
        <button aria-pressed={view === 'chords'} onClick={() => setView('chords')}>Chords</button>
        <button aria-pressed={view === 'live'} onClick={() => setView('live')}>Live chord</button>
      </span>
      <span className="seg" role="group" aria-label="Window size">
        <button onClick={() => resize(-10)} aria-label="Make everything smaller" title="Smaller" disabled={uiScale <= 70}><ZoomOut size={16} /></button>
        <button className="seg-label" onClick={() => setAppearance({ uiScale: 100 })} title="Reset size" aria-label={`Size ${uiScale} percent. Press to reset to 100`}>{uiScale}%</button>
        <button onClick={() => resize(10)} aria-label="Make everything larger" title="Larger" disabled={uiScale >= 160}><ZoomIn size={16} /></button>
      </span>
      <button className="icon-btn" aria-label="Settings" onClick={() => setDialog('settings')}><Settings size={18} /></button>
    </header>
  )
}
