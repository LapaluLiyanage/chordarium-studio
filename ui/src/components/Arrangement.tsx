import { Lock, LockOpen, RefreshCw } from 'lucide-react'
import { COPY } from '../copy'
import { ROLE_LABEL } from '../sections'
import { partsFor, planFor, sectionQuarters, useStore } from '../store'
import { PPQ, ROLES } from '../types'
import { MiniPianoRoll } from './MiniPianoRoll'
import { Playhead } from './Playhead'
import { fileDragHandlers } from '../fileDrag'

export function Arrangement() {
  const { snap, selectedId, arrange, regenerate, toggleLock, setNotes, inspector, setInspector, thinking, styles } = useStore()
  const parts = partsFor(snap, selectedId)
  const plan = planFor(snap, selectedId)
  const sec = snap?.song?.sections.find((s) => s.id === selectedId)
  const q = sectionQuarters(snap, selectedId)


  if (!snap?.song || !sec) return <section className="card"><h2>Arrangement</h2><div className="empty">{COPY.noSong}</div></section>
  return (
    <section className="card" aria-label="Arrangement">
      <div className="row wrap-row"><h2 className="grow">{sec.name}</h2>
        <select className="field" aria-label="Style" value={plan?.style ?? styles[0]?.id ?? ''} onChange={(e) => void arrange([sec.id], e.target.value, plan?.dynamics)}>
          {styles.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        {parts.length > 0 && <button className="btn drag-src" title="Drag onto the Cubase project area: one track per part" aria-label="Drag all tracks to Cubase" {...fileDragHandlers(`section:${sec.id}`)}>⠿ Drag all to Cubase</button>}
        <button className="btn primary" disabled={thinking} onClick={() => void arrange([sec.id], plan?.style, plan?.dynamics ?? 'medium')}>{parts.length ? 'Re-arrange' : 'Arrange'}</button>
      </div>
      {thinking && <p className="muted" aria-live="polite">{COPY.planning(sec.name)}</p>}
      {parts.length === 0 && !thinking && <div className="empty">No parts yet. Press Arrange or ask the assistant.</div>}
      <div className="roll">
        {ROLES.map((role) => {
          const p = parts.find((x) => x.role === role); if (!p) return null
          return (
            <div key={p.id} className={`lane ${inspector === role ? 'sel' : ''}`} style={{ ['--c' as string]: `var(--role-${role})` }}>
              <div className="head drag-src" title="Drag onto a Cubase track to add this part" {...fileDragHandlers(p.id)}>
                <button className="icon-btn" style={{ width: '100%', justifyContent: 'flex-start' }} onClick={() => setInspector(role)} aria-label={`Inspect ${ROLE_LABEL[role]}`}><strong>{ROLE_LABEL[role]}</strong></button>
                <div className="row">
                  <button className="icon-btn" aria-label={p.locked ? `Unlock ${role}` : `Lock ${role}`} title={p.locked ? COPY.locked(ROLE_LABEL[role]) : 'Lock'} onClick={() => void toggleLock(p.id)}>{p.locked ? <Lock size={14} /> : <LockOpen size={14} />}</button>
                  <button className="icon-btn" aria-label={`Regenerate ${role}`} disabled={p.locked} onClick={() => void regenerate(p.id)}><RefreshCw size={14} /></button>
                  <span className="muted">{p.notes.length}</span>
                </div>
              </div>
              <MiniPianoRoll part={p} ticks={q * PPQ} colorVar={`--role-${role}`} tall={inspector === role} onChange={(notes) => void setNotes(p.id, notes)} />
            </div>
          )
        })}
        {parts.length > 0 && <Playhead quarters={q} />}
      </div>
    </section>
  )
}
