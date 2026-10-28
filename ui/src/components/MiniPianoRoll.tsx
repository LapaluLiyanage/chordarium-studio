import { useEffect, useRef } from 'react'
import type { Part } from '../types'

/** Tiny canvas piano roll. Colours are read from CSS variables so the theme stays in tokens.css. */
export function MiniPianoRoll({ part, ticks, colorVar }: { part: Part; ticks: number; colorVar: string }) {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const c = ref.current; if (!c) return
    const ctx = c.getContext('2d'); if (!ctx) return
    const w = (c.width = c.clientWidth || 300), h = (c.height = 64)
    ctx.clearRect(0, 0, w, h)
    if (!part.notes.length) return
    const cs = getComputedStyle(c)
    ctx.fillStyle = cs.getPropertyValue(colorVar).trim() || '#888'
    const lo = Math.min(...part.notes.map((n) => n.pitch)), hi = Math.max(...part.notes.map((n) => n.pitch))
    const span = Math.max(12, hi - lo + 1)
    for (const n of part.notes) {
      const x = (n.start / ticks) * w, nw = Math.max(2, (n.duration / ticks) * w - 1)
      const y = h - 4 - ((n.pitch - lo) / span) * (h - 8)
      ctx.globalAlpha = 0.4 + 0.6 * (n.velocity / 127)
      ctx.fillRect(x, y - 3, nw, 4)
    }
  }, [part, ticks, colorVar])
  return <canvas ref={ref} role="img" aria-label={`${part.role} notes: ${part.notes.length}`} />
}
