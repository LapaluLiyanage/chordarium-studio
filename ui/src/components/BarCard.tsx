import { useState } from 'react'
import { chordSuggestions } from '../chords'
import { useStore } from '../store'
import type { Bar } from '../types'
import { ChordSymbol } from './ChordSymbol'

/** Split a bar into one more chord, sharing the bar's beats evenly (the new chord repeats the last symbol). */
export function splitBar(bar: Bar) {
  const total = bar.chords.reduce((t, c) => t + c.beats, 0), n = bar.chords.length + 1
  bar.chords.push({ symbol: bar.chords.at(-1)!.symbol, beats: total / n })
  bar.chords.forEach((c) => { c.beats = total / n })
}

/** Drop the last chord of a bar and share the beats evenly between the rest. */
export function mergeBar(bar: Bar) {
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

/**
 * One bar as a card: its chords share the width by beats, a tick under the card marks each beat,
 * and hover tools split, merge or delete it. `flagged` bars get the dashed outline from the parser's warnings.
 */
export function BarCard({ sectionId, index, bar, beatsPerBar, canDelete, flagged = false, board = false }: {
  sectionId: string; index: number; bar: Bar; beatsPerBar: number; canDelete: boolean; flagged?: boolean; board?: boolean
}) {
  const editBars = useStore((s) => s.editBars)
  const n = index + 1
  return (
    <div className={`bar${board ? ' board-bar' : ''}${flagged ? ' flagged' : ''}`} style={{ ['--beats' as string]: beatsPerBar }}>
      {!board && <span className="num">{n}</span>}
      {bar.chords.map((c, ci) => (
        <span key={ci} className="slot" style={{ flex: `${c.beats} 1 0` }}>
          <Cell sectionId={sectionId} bar={index} slot={ci} symbol={c.symbol} />
        </span>
      ))}
      {flagged && <span className="flag" title="Check this bar: the parser had to guess" aria-label="Check this bar">?</span>}
      <span className="ticks" aria-hidden />
      <span className="bar-tools">
        <button className="icon-btn" aria-label={`Add a chord to bar ${n}`} title="Split bar: add a chord" onClick={() => void editBars(sectionId, (bars) => splitBar(bars[index]))}>+</button>
        {bar.chords.length > 1 && <button className="icon-btn" aria-label={`Remove last chord from bar ${n}`} title="Remove last chord" onClick={() => void editBars(sectionId, (bars) => mergeBar(bars[index]))}>−</button>}
        {canDelete && <button className="icon-btn" aria-label={`Delete bar ${n}`} title="Delete bar" onClick={() => void editBars(sectionId, (bars) => { bars.splice(index, 1) })}>×</button>}
      </span>
    </div>
  )
}
