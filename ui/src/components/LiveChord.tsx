import { useEffect, useState } from 'react'
import { getBridge } from '../bridge'
import { useStore } from '../store'
import { ChordSymbol } from './ChordSymbol'

export function LiveChord() {
  const { snap, selectedId } = useStore()
  const sec = snap?.song?.sections.find((s) => s.id === selectedId)
  const [qn, setQn] = useState(0)
  useEffect(() => { const id = setInterval(() => setQn(getBridge().position().quarters), 100); return () => clearInterval(id) }, [])
  if (!sec) return <div className="live muted">—</div>
  let acc = 0, cur = sec.bars[0]?.chords[0]?.symbol ?? '—'
  const total = sec.bars.reduce((t, b) => t + b.chords.reduce((u, c) => u + c.beats, 0), 0) || 1
  const pos = qn % total
  outer: for (const b of sec.bars) for (const c of b.chords) { if (pos >= acc && pos < acc + c.beats) { cur = c.symbol; break outer } acc += c.beats }
  return <div className="live" aria-live="off"><ChordSymbol symbol={cur} /></div>
}
