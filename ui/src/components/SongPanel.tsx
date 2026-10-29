import { useState } from 'react'
import { chordSuggestions } from '../chords'
import { COPY } from '../copy'
import { SECTION_COLOR } from '../sections'
import { useStore } from '../store'
import { ChordSymbol } from './ChordSymbol'

/** Split a bar into one more chord, sharing the bar's beats evenly (new chord repeats the last symbol). */
function splitBar(bar: { chords: { symbol: string; beats: number }[] }) {
  const total = bar.chords.reduce((t, c) => t + c.beats, 0), n = bar.chords.length + 1
  bar.chords.push({ symbol: bar.chords.at(-1)!.symbol, beats: total / n })
  bar.chords.forEach((c) => { c.beats = total / n })
}

function mergeBar(bar: { chords: { symbol: string; beats: number }[] }) {
  const total = bar.chords.reduce((t, c) => t + c.beats, 0)
  bar.chords.pop()
  bar.chords.forEach((c) => { c.beats = total / bar.chords.length })
}

function Cell({ sectionId, bar, slot, symbol }: { sectionId: string; bar: number; slot: number; symbol: string }) {
  const patch = useStore((s) => s.patchChord)
  const [edit, setEdit] = useState(false)
  const [val, setVal] = useState(symbol)
  const commit = async (v: string) => {
    setEdit(false)
    if (v && v !== symbol) await patch(sectionId, bar, slot, v)
  }
  if (!edit) return <button className="cell" aria-label={`Bar ${bar + 1} chord ${symbol}`} onClick={() => { setVal(symbol); setEdit(true) }}><ChordSymbol symbol={symbol} /></button>
  return (
    <span style={{ flex: 1, position: 'relative' }}>
      <input className="cell-input" autoFocus aria-label="Chord symbol" value={val} onChange={(e) => setVal(e.target.value)}
        onBlur={() => void commit(val.trim())}
        onKeyDown={(e) => { if (e.key === 'Enter') void commit(val.trim()); if (e.key === 'Escape') setEdit(false) }} />
      <span className="suggest">{chordSuggestions(val).map((c) => <button key={c} className="chip" onMouseDown={(e) => { e.preventDefault(); void commit(c) }}>{c}</button>)}</span>
    </span>
  )
}

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
        {sec.bars.map((b, bi) => (
          <div key={bi} className="bar"><span className="num">{bi + 1}</span>
            {b.chords.map((c, ci) => <Cell key={ci} sectionId={sec.id} bar={bi} slot={ci} symbol={c.symbol} />)}
            <span className="bar-tools">
              <button className="icon-btn" aria-label={`Add a chord to bar ${bi + 1}`} title="Split bar: add a chord" onClick={() => void editBars(sec.id, (bars) => splitBar(bars[bi]))}>+</button>
              {b.chords.length > 1 && <button className="icon-btn" aria-label={`Remove last chord from bar ${bi + 1}`} title="Remove last chord" onClick={() => void editBars(sec.id, (bars) => mergeBar(bars[bi]))}>−</button>}
              {sec.bars.length > 1 && <button className="icon-btn" aria-label={`Delete bar ${bi + 1}`} title="Delete bar" onClick={() => void editBars(sec.id, (bars) => { bars.splice(bi, 1) })}>×</button>}
            </span>
          </div>
        ))}
      </div>
      <div className="row" style={{ marginTop: 8 }}>
        <button className="btn" onClick={() => void editBars(sec.id, (bars, beats) => { const last = bars[bars.length - 1]?.chords.at(-1)?.symbol ?? 'C'; bars.push({ chords: [{ symbol: last, beats }] }) })}>Add bar</button>
        <button className="btn" onClick={() => void editBars(sec.id, (bars, beats) => { for (let i = 0; i < 4; i++) { const last = bars[bars.length - 1]?.chords.at(-1)?.symbol ?? 'C'; bars.push({ chords: [{ symbol: last, beats }] }) } })}>Add 4 bars</button>
      </div>
      {song.warnings.length > 0 && <ul className="muted">{song.warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
    </section>
  )
}
