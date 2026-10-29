import { COPY } from '../copy'
import { SECTION_COLOR } from '../sections'
import { useStore } from '../store'
import { BarCard } from './BarCard'

/** Compact chord grid for the selected section, shown beside the arrangement. The Chords view shows the whole song large. */
export function SongPanel() {
  const { snap, selectedId, selectSection, setDialog, editBars, newSong } = useStore()
  const song = snap?.song
  if (!song) return (
    <section className="card"><h2>Song</h2>
      <div className="empty">{COPY.noSong}<br /><br /><button className="btn primary" onClick={() => setDialog('paste')}>Paste chord sheet</button></div>
    </section>
  )
  const sec = song.sections.find((s) => s.id === selectedId) ?? song.sections[0]
  const flagged = song.warnings.filter((w) => /^(Bar|.*bar)/i.test(w)).length
  const beats = song.time_signature[0]
  const repeatLast = (bars: { chords: { symbol: string; beats: number }[] }[]) => bars.push({ chords: [{ symbol: bars[bars.length - 1]?.chords.at(-1)?.symbol ?? 'C', beats }] })
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
        {sec.bars.map((b, bi) => <BarCard key={bi} sectionId={sec.id} index={bi} bar={b} beatsPerBar={beats} canDelete={sec.bars.length > 1} />)}
      </div>
      <div className="row" style={{ marginTop: 8 }}>
        <button className="btn" onClick={() => void editBars(sec.id, (bars) => repeatLast(bars))}>Add bar</button>
        <button className="btn" onClick={() => void editBars(sec.id, (bars) => { for (let i = 0; i < 4; i++) repeatLast(bars) })}>Add 4 bars</button>
      </div>
      {song.warnings.length > 0 && <ul className="muted">{song.warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
    </section>
  )
}
