import { useEffect, useState } from 'react'
import { getBridge } from './bridge'
import type { Section } from './types'

export interface Located { bar: number; slot: number; symbol: string }

/** The bar, chord slot and symbol sounding at `quarters` into a section, looping when the position runs past its end. */
export function locate(sec: Section | undefined, quarters: number): Located | null {
  if (!sec || !sec.bars.length) return null
  const total = sec.bars.reduce((t, b) => t + b.chords.reduce((u, c) => u + c.beats, 0), 0)
  if (total <= 0) return null
  const pos = ((quarters % total) + total) % total
  let at = 0
  for (let bar = 0; bar < sec.bars.length; bar++) {
    const chords = sec.bars[bar].chords
    for (let slot = 0; slot < chords.length; slot++) {
      if (pos < at + chords[slot].beats) return { bar, slot, symbol: chords[slot].symbol }
      at += chords[slot].beats
    }
  }
  const last = sec.bars.length - 1
  return { bar: last, slot: sec.bars[last].chords.length - 1, symbol: sec.bars[last].chords.at(-1)!.symbol }
}

/** The chord playing in `sec` right now, or null when nothing is playing. Polls the bridge about 12 times a second. */
export function useNowPlaying(sec: Section | undefined): Located | null {
  const [now, setNow] = useState<Located | null>(null)
  useEffect(() => {
    const tick = () => {
      const p = getBridge().position()
      const next = p.playing ? locate(sec, p.quarters) : null
      setNow((prev) => (prev?.bar === next?.bar && prev?.slot === next?.slot && prev?.symbol === next?.symbol ? prev : next))
    }
    tick()
    const id = setInterval(tick, 80)
    return () => clearInterval(id)
  }, [sec])
  return now
}
