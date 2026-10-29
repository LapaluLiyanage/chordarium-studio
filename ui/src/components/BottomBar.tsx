import { Download, Pause, Play, Repeat, Volume2, VolumeX } from 'lucide-react'
import { partsFor, useStore } from '../store'
import { ROLES } from '../types'
import { ROLE_LABEL } from '../sections'

export function BottomBar() {
  const { snap, selectedId, playing, play, stop, loop, setLoop, builtInSound, setBuiltInSound, mix, setMix, syncMode, setSync, exportMidi, transport } = useStore()
  const has = partsFor(snap, selectedId).length > 0
  return (
    <footer className="bottom">
      <button className="btn primary" disabled={!has} onClick={() => (playing ? stop() : play())} aria-label={playing ? 'Stop preview' : 'Play preview'}>
        {playing ? <Pause size={16} /> : <Play size={16} />}
      </button>
      <button className="icon-btn" aria-pressed={loop} aria-label="Loop" onClick={() => setLoop(!loop)}><Repeat size={16} color={loop ? 'var(--brand)' : undefined} /></button>
      <button className="btn" aria-pressed={!builtInSound} aria-label={builtInSound ? 'Mute built-in sound' : 'Unmute built-in sound'}
        title={builtInSound ? 'Mute the plugin\'s built-in preview sound (MIDI still plays out to your instruments)' : 'Built-in sound is muted. Click to hear it again'} onClick={() => setBuiltInSound(!builtInSound)}>
        {builtInSound ? <Volume2 size={16} /> : <VolumeX size={16} />} {builtInSound ? 'Preview sound' : 'Muted'}
      </button>
      <select className="field" aria-label="Sync mode" value={syncMode} onChange={(e) => setSync(e.target.value as 'host' | 'free')}>
        <option value="free">Free (own clock)</option><option value="host">Follow Cubase</option>
      </select>
      <span className="grow" />
      {ROLES.map((r) => (
        <span key={r} className="mix" style={{ color: `var(--role-${r})` }}>
          <span>{ROLE_LABEL[r]}</span>
          <button className="chip" aria-pressed={mix[r].mute} aria-label={`Mute ${r}`} onClick={() => setMix(r, { mute: !mix[r].mute })}>M</button>
          <button className="chip" aria-pressed={mix[r].solo} aria-label={`Solo ${r}`} onClick={() => setMix(r, { solo: !mix[r].solo })}>S</button>
          <input className="vol" style={{ ['--v' as string]: `${Math.round(mix[r].gain * 100)}%` }} type="range" aria-label={`${r} volume`} title={`${ROLE_LABEL[r]} volume`} min={0} max={1} step={0.01} value={mix[r].gain} onChange={(e) => setMix(r, { gain: Number(e.target.value) })} />
        </span>
      ))}
      <span className="grow" />
      <button className="btn" onClick={() => void transport('to_start')}>⏮</button>
      <button className="btn" disabled={!has} onClick={() => void exportMidi('section')}><Download size={14} /> Export section</button>
      <button className="btn" disabled={!snap?.song} onClick={() => void exportMidi('song')}>Export song</button>
    </footer>
  )
}
