import { useEffect, useRef } from 'react'
import type { NoteEvent, Part } from '../types'

const GRID = 240   // snap to 8th notes (PPQ 480)
const LOW = 0, HIGH = 127

/** Pitch range shown for a part. Wider than the notes so there is room to add one above or below. */
function range(notes: NoteEvent[], pad: number) {
  if (!notes.length) return { lo: 48, hi: 72 }
  const lo = Math.max(LOW, Math.min(...notes.map((n) => n.pitch)) - pad)
  const hi = Math.min(HIGH, Math.max(...notes.map((n) => n.pitch)) + pad)
  return hi - lo < 11 ? { lo, hi: lo + 11 } : { lo, hi }
}

/**
 * Canvas piano roll. Colours are read from CSS variables so the theme stays in tokens.css.
 * With `onChange` it is editable: click empty space to add an 8th note, click a note to delete it.
 */
export function MiniPianoRoll({ part, ticks, colorVar, tall = false, onChange }: {
  part: Part; ticks: number; colorVar: string; tall?: boolean; onChange?: (notes: NoteEvent[]) => void
}) {
  const ref = useRef<HTMLCanvasElement>(null)
  const height = tall ? 160 : 64
  const pad = onChange && tall ? 4 : 0

  useEffect(() => {
    const c = ref.current; if (!c) return
    const ctx = c.getContext('2d'); if (!ctx) return
    const w = (c.width = c.clientWidth || 300), h = (c.height = height)
    ctx.clearRect(0, 0, w, h)
    const { lo, hi } = range(part.notes, pad), rows = hi - lo + 1, rowH = (h - 8) / rows
    const color = getComputedStyle(c).getPropertyValue(colorVar).trim() || '#888'
    if (tall) {   // beat lines so the grid is visible while editing
      ctx.fillStyle = color; ctx.globalAlpha = 0.12
      for (let t = 0; t < ticks; t += 480) ctx.fillRect((t / ticks) * w, 0, 1, h)
    }
    ctx.fillStyle = color
    for (const n of part.notes) {
      const x = (n.start / ticks) * w, nw = Math.max(2, (n.duration / ticks) * w - 1)
      const y = h - 4 - (n.pitch - lo + 1) * rowH
      ctx.globalAlpha = 0.4 + 0.6 * (n.velocity / 127)
      ctx.fillRect(x, y, nw, Math.max(tall ? 5 : 4, rowH - 1))
    }
  }, [part, ticks, colorVar, height, pad, tall])

  const edit = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!onChange || !ref.current) return
    const box = ref.current.getBoundingClientRect()
    const x = e.clientX - box.left, y = e.clientY - box.top, w = box.width
    const { lo, hi } = range(part.notes, pad), rows = hi - lo + 1, rowH = (height - 8) / rows
    const tick = (x / w) * ticks
    const pitch = Math.max(LOW, Math.min(HIGH, lo + Math.floor((height - 4 - y) / rowH)))
    const hit = part.notes.findIndex((n) => n.pitch === pitch && tick >= n.start && tick <= n.start + n.duration)
    if (hit >= 0) { onChange(part.notes.filter((_, i) => i !== hit)); return }
    const start = Math.max(0, Math.min(ticks - GRID, Math.floor(tick / GRID) * GRID))
    const [vlo, vhi] = part.spec.velocity
    onChange([...part.notes, { pitch, start, duration: GRID, velocity: Math.round((vlo + vhi) / 2) }])
  }

  return <canvas ref={ref} role="img" style={{ height, cursor: onChange ? 'crosshair' : undefined }}
    aria-label={`${part.role} notes: ${part.notes.length}${onChange ? '. Click empty space to add a note, click a note to delete it.' : ''}`}
    onPointerDown={edit} />
}
