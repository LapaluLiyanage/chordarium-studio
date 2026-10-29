import { COPY } from '../copy'
import { SECTION_COLOR } from '../sections'
import { useStore } from '../store'
import { BarCard } from './BarCard'

/** Compact chord grid for the selected section, shown beside the arrangement. The Chords view shows the whole song large. */
export function SongPanel() {
  const { snap, selectedId, selectSection, setDialog, newSong, setView } = useStore()
  const song = snap?.song
  if (!song) return (
    <section className="card"><h2>Song</h2>
      <div className="empty">{COPY.noSong}<br /><br /><button className="btn primary" onClick={() => setDialog('paste')}>Paste chord sheet</button></div>
    </section>
  )
  const sec = song.sections.find((s) => s.id === selectedId) ?? song.sections[0]
  const flagged = song.warnings.filter((w) => /^(Bar|.*bar)/i.test(w)).length
  const beats = song.time_signature[0]
  return (
    <section className="card" aria-label="Song">
      <div className="row"><h2 className="grow">{song.title}</h2><button className="btn" onClick={() => void newSong()} title="Start an empty song">New</button><button className="btn" onClick={() => setDialog('paste')}>Replace</button></div>
      {song.warnings.length > 0 && <p className="chip" role="alert">{COPY.barsNeedCheck(flagged || song.warnings.length)}</p>}
      <div className="sections" role="tablist">
        {song.sections.map((s) => (
          <button key={s.id} role="tab" className="sec-tab" aria-selected={s.id === sec.id} style={{ ['--c' as string]: SECTION_COLOR[s.kind] }} onClick={() => void selectSection(s.id)}>{s.name}</button>
        ))}
      </div>
      <div className="grid">
        {sec.bars.map((b, bi) => <BarCard key={bi} sectionId={sec.id} index={bi} bar={b} beatsPerBar={beats} canDelete={false} readOnly />)}
      </div>
      <p className="muted" style={{ marginTop: 8 }}>To change chords, open the <button className="btn" onClick={() => setView('chords')}>Chords view</button>.</p>
      {song.warnings.length > 0 && <ul className="muted">{song.warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
    </section>
  )
}
