import { Pause, Play } from 'lucide-react'
import { useState } from 'react'
import { SECTION_COLOR } from '../sections'
import { useStore } from '../store'
import { BarCard } from './BarCard'

const PER_ROW = [2, 4, 8] as const

/** Full-width chord board: every section as big bar cards, with bars per row, transpose and simplify. */
export function ChordBoard() {
  const { snap, selectedId, selectSection, playing, play, stop, transposeBy, simplifyAll, setDialog } = useStore()
  const song = snap?.song
  const [perRow, setPerRow] = useState<number>(() => { try { return Number(localStorage.getItem('chordarium.perRow')) || 4 } catch { return 4 } })
  const [shift, setShift] = useState(0)
  if (!song) return <section className="board"><div className="empty">Paste a chord sheet to begin.<br /><br /><button className="btn primary" onClick={() => setDialog('paste')}>Paste chord sheet</button></div></section>

  const choose = (n: number) => { setPerRow(n); try { localStorage.setItem('chordarium.perRow', String(n)) } catch { /* private mode */ } }
  const move = async (by: number) => { if (await transposeBy(by)) setShift((s) => s + by) }
  // The parser reports guesses as "Bar N: ..." (N counts bars across the whole song); those bars get the dashed outline.
  const flaggedBars = new Set(song.warnings.flatMap((w) => { const m = /^Bar (\d+)/i.exec(w); return m ? [Number(m[1])] : [] }))
  let first = 1
  return (
    <section className="board" aria-label="Chord board">
      <h1>{song.title}</h1>
      <p className="board-meta">{[song.key ? `Key ${song.key} ${song.mode}` : null, `${song.tempo_bpm} BPM`, song.time_signature.join('/')].filter(Boolean).join(' · ')}</p>
      <div className="board-toolbar">
        <button className="btn primary pill-lg" disabled={!selectedId} onClick={() => (playing ? stop() : play())} aria-label={playing ? 'Stop preview' : 'Play selected section'}>
          {playing ? <Pause size={16} /> : <Play size={16} />} {playing ? 'STOP' : 'PLAY'}
        </button>
        <span className="seg" role="group" aria-label="Transpose">
          <button onClick={() => void move(-1)} aria-label="Transpose down one semitone">−</button>
          <span className="seg-label">TRANSPOSE {shift > 0 ? `+${shift}` : shift}</span>
          <button onClick={() => void move(1)} aria-label="Transpose up one semitone">+</button>
        </span>
        <span className="seg" role="group" aria-label="Bars per row">
          {PER_ROW.map((n) => <button key={n} aria-pressed={perRow === n} onClick={() => choose(n)}>{n} / ROW</button>)}
        </span>
        <button className="btn pill-lg" onClick={() => void simplifyAll()} title="Reduce every chord to its triad">SIMPLIFY</button>
      </div>
      {song.sections.map((sec) => {
        const start = first; first += sec.bars.length
        return (
          <div key={sec.id} className="board-section">
            <div className="board-sec">
              <button className="pill-sec" style={{ ['--c' as string]: SECTION_COLOR[sec.kind] }} aria-pressed={sec.id === selectedId} onClick={() => void selectSection(sec.id)}>{sec.name}</button>
              <span className="rule" />
              <span className="muted bars-range">BARS {start}–{start + sec.bars.length - 1}</span>
            </div>
            <div className="board-grid" style={{ ['--per-row' as string]: perRow }}>
              {sec.bars.map((b, bi) => <BarCard key={bi} board sectionId={sec.id} index={bi} bar={b} beatsPerBar={song.time_signature[0]} canDelete={sec.bars.length > 1} flagged={flaggedBars.has(start + bi)} />)}
            </div>
          </div>
        )
      })}
    </section>
  )
}
