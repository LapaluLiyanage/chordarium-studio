import { useEffect, useRef, useState } from 'react'
import type { NoteEvent, Part } from '../types'

const GRID = 240          // snap to 8th notes (PPQ 480)
const MIN_LEN = 120       // shortest note when resizing: a 16th
const EDGE_PX = 7         // grab zone at a note's right end for resizing
const LOW = 0, HIGH = 127
const NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
const noteName = (p: number) => `${NAMES[p % 12]}${Math.floor(p / 12) - 1}`
const keyOf = (n: NoteEvent) => `${n.pitch}:${n.start}`
const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v))

/** Pitch range shown for a part. Wider than the notes so there is room to add one above or below. */
function range(notes: NoteEvent[], pad: number) {
  if (!notes.length) return { lo: 48, hi: 72 }
  const lo = Math.max(LOW, Math.min(...notes.map((n) => n.pitch)) - pad)
  const hi = Math.min(HIGH, Math.max(...notes.map((n) => n.pitch)) + pad)
  return hi - lo < 11 ? { lo, hi: lo + 11 } : { lo, hi }
}

type Drag = { mode: 'move' | 'resize'; orig: NoteEvent; x0: number; y0: number; lo: number; hi: number; moved: boolean }

/**
 * Canvas piano roll. Colours are read from CSS variables so the theme stays in tokens.css.
 * With `onChange` it is editable:
 *  - click empty space: add an 8th note
 *  - drag a note: move it in time and pitch; drag its right end: resize
 *  - click a note to select it, then Up/Down = velocity, Left/Right = nudge, Shift+Up/Down = pitch, Delete = remove
 *  - double-click a note: remove it
 */
export function MiniPianoRoll({ part, ticks, colorVar, tall = false, onChange }: {
  part: Part; ticks: number; colorVar: string; tall?: boolean; onChange?: (notes: NoteEvent[]) => void
}) {
  const ref = useRef<HTMLCanvasElement>(null)
  const drag = useRef<Drag | null>(null)
  const [draft, setDraft] = useState<NoteEvent[] | null>(null)   // notes while a drag is in progress, until the core confirms
  const [selected, setSelected] = useState<string | null>(null)
  const height = tall ? 160 : 64
  const pad = onChange && tall ? 4 : 0
  const notes = draft ?? part.notes

  useEffect(() => { setDraft(null) }, [part.notes])

  useEffect(() => {
    const c = ref.current; if (!c) return
    const ctx = c.getContext('2d'); if (!ctx) return
    const w = (c.width = c.clientWidth || 300), h = (c.height = height)
    ctx.clearRect(0, 0, w, h)
    const { lo, hi } = drag.current ? drag.current : range(part.notes, pad), rows = hi - lo + 1, rowH = (h - 8) / rows
    const color = getComputedStyle(c).getPropertyValue(colorVar).trim() || '#888'
    if (tall) {   // beat lines so the grid is visible while editing
      ctx.fillStyle = color; ctx.globalAlpha = 0.12
      for (let t = 0; t < ticks; t += 480) ctx.fillRect((t / ticks) * w, 0, 1, h)
    }
    for (const n of notes) {
      const x = (n.start / ticks) * w, nw = Math.max(2, (n.duration / ticks) * w - 1)
      const y = h - 4 - (n.pitch - lo + 1) * rowH, nh = Math.max(tall ? 5 : 4, rowH - 1)
      ctx.fillStyle = color; ctx.globalAlpha = 0.4 + 0.6 * (n.velocity / 127)
      ctx.fillRect(x, y, nw, nh)
      if (onChange && keyOf(n) === selected) { ctx.globalAlpha = 1; ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.5; ctx.strokeRect(x, y, nw, nh) }
    }
  }, [notes, part.notes, ticks, colorVar, height, pad, tall, selected, onChange])

  const geometry = () => {
    const box = ref.current!.getBoundingClientRect()
    const r = drag.current ?? range(part.notes, pad)
    return { box, lo: r.lo, hi: r.hi, rowH: (height - 8) / (r.hi - r.lo + 1) }
  }
  const pitchAt = (y: number, lo: number, rowH: number) => clamp(lo + Math.floor((height - 4 - y) / rowH), LOW, HIGH)
  /** Topmost note under the pointer, and whether the pointer is on its right-hand resize edge. */
  const hitTest = (x: number, y: number) => {
    const { box, lo, rowH } = geometry(), pitch = pitchAt(y, lo, rowH), w = box.width
    for (let i = notes.length - 1; i >= 0; i--) {
      const n = notes[i]; if (n.pitch !== pitch) continue
      const x0 = (n.start / ticks) * w, x1 = x0 + Math.max(2, (n.duration / ticks) * w)
      if (x >= x0 - 1 && x <= x1 + 1) return { index: i, edge: x1 - x <= EDGE_PX && x1 - x0 > EDGE_PX * 1.5 }
    }
    return null
  }
  const replace = (i: number, patch: Partial<NoteEvent>) => notes.map((n, k) => (k === i ? { ...n, ...patch } : n))

  const down = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!onChange || !ref.current) return
    ref.current.focus()
    const box = ref.current.getBoundingClientRect(), x = e.clientX - box.left, y = e.clientY - box.top
    const hit = hitTest(x, y)
    if (hit) {
      const orig = notes[hit.index], { lo, hi } = range(part.notes, pad)
      drag.current = { mode: hit.edge ? 'resize' : 'move', orig, x0: x, y0: y, lo, hi, moved: false }
      setSelected(keyOf(orig))
      ref.current.setPointerCapture?.(e.pointerId)
      return
    }
    const { lo, rowH } = geometry()
    const start = clamp(Math.floor(((x / box.width) * ticks) / GRID) * GRID, 0, Math.max(0, ticks - GRID))
    const [vlo, vhi] = part.spec.velocity
    const added = { pitch: pitchAt(y, lo, rowH), start, duration: GRID, velocity: Math.round((vlo + vhi) / 2) }
    setSelected(keyOf(added))
    onChange([...notes, added])
  }

  const move = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const d = drag.current; if (!d || !onChange || !ref.current) return
    const box = ref.current.getBoundingClientRect(), x = e.clientX - box.left, y = e.clientY - box.top
    if (!d.moved && Math.hypot(x - d.x0, y - d.y0) < 3) return
    d.moved = true
    const rowH = (height - 8) / (d.hi - d.lo + 1)
    const i = notes.findIndex((n) => keyOf(n) === keyOf(d.orig)); if (i < 0) return
    if (d.mode === 'resize') {
      const end = clamp(Math.round(((x / box.width) * ticks) / MIN_LEN) * MIN_LEN, d.orig.start + MIN_LEN, ticks)
      setDraft(replace(i, { duration: end - d.orig.start }))
    } else {
      const dTick = Math.round((((x - d.x0) / box.width) * ticks) / GRID) * GRID
      const dRow = Math.round((d.y0 - y) / rowH)
      const start = clamp(d.orig.start + dTick, 0, Math.max(0, ticks - d.orig.duration))
      const pitch = clamp(d.orig.pitch + dRow, LOW, HIGH)
      const next = replace(i, { start, pitch })
      setDraft(next); setSelected(keyOf(next[i]))
    }
  }

  const up = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const d = drag.current; drag.current = null
    ref.current?.releasePointerCapture?.(e.pointerId)
    if (d?.moved && draft && onChange) onChange(draft)
    else if (d) setDraft(null)
  }

  const dbl = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!onChange || !ref.current) return
    const box = ref.current.getBoundingClientRect(), hit = hitTest(e.clientX - box.left, e.clientY - box.top)
    if (hit) { setSelected(null); onChange(notes.filter((_, i) => i !== hit.index)) }
  }

  const key = (e: React.KeyboardEvent<HTMLCanvasElement>) => {
    if (!onChange || !selected) return
    const i = notes.findIndex((n) => keyOf(n) === selected); if (i < 0) return
    const n = notes[i]; let patch: Partial<NoteEvent> | null = null
    if (e.key === 'Delete' || e.key === 'Backspace') { e.preventDefault(); setSelected(null); onChange(notes.filter((_, k) => k !== i)); return }
    if (e.key === 'ArrowUp') patch = e.shiftKey ? { pitch: clamp(n.pitch + 1, LOW, HIGH) } : { velocity: clamp(n.velocity + 5, 1, 127) }
    else if (e.key === 'ArrowDown') patch = e.shiftKey ? { pitch: clamp(n.pitch - 1, LOW, HIGH) } : { velocity: clamp(n.velocity - 5, 1, 127) }
    else if (e.key === 'ArrowRight') patch = { start: clamp(n.start + GRID, 0, Math.max(0, ticks - n.duration)) }
    else if (e.key === 'ArrowLeft') patch = { start: clamp(n.start - GRID, 0, Math.max(0, ticks - n.duration)) }
    if (!patch) return
    e.preventDefault()
    const updated = { ...n, ...patch }
    setSelected(keyOf(updated))
    onChange(notes.map((m, k) => (k === i ? updated : m)))
  }

  const sel = selected ? notes.find((n) => keyOf(n) === selected) : undefined
  return (
    <div>
      <canvas ref={ref} role="img" tabIndex={onChange ? 0 : undefined} style={{ height, cursor: onChange ? 'crosshair' : undefined, touchAction: 'none' }}
        aria-label={`${part.role} notes: ${part.notes.length}${onChange ? '. Click empty space to add a note, drag a note to move it, drag its right end to resize, double-click to delete.' : ''}`}
        onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up} onDoubleClick={dbl} onKeyDown={key} />
      {onChange && tall && (
        <div className="muted" style={{ fontSize: '.8em', minHeight: '1.4em' }} aria-live="polite">
          {sel ? `${noteName(sel.pitch)} · velocity ${sel.velocity} · ${(sel.duration / 480).toFixed(2)} beats — ↑↓ velocity, ⇧↑↓ pitch, ←→ nudge, Delete removes` : 'Click to add · drag to move · drag the right end to resize · double-click to delete'}
        </div>
      )}
    </div>
  )
}
