import * as Slider from '@radix-ui/react-slider'
import { COPY } from '../copy'
import { PATTERN_LABEL, REGISTER_LABEL, ROLE_LABEL } from '../sections'
import { partsFor, useStore } from '../store'
import { REGISTERS, type Fills } from '../types'

export function Inspector() {
  const { snap, selectedId, inspector, styles, editPart } = useStore()
  const part = partsFor(snap, selectedId).find((p) => p.role === inspector)
  const style = styles.find((s) => s.id === snap?.plans[selectedId ?? '']?.style)
  if (!part) return <aside className="card"><h2>Inspector</h2><div className="empty">Select a part lane to tweak it.</div></aside>
  const spec = part.spec, off = part.locked
  const patterns = style?.patterns[part.role] ?? [spec.pattern]
  return (
    <aside className="card" aria-label="Inspector">
      <h2>{ROLE_LABEL[part.role]}</h2>
      {off && <p className="chip">{COPY.locked(ROLE_LABEL[part.role])}</p>}
      <label>Pattern<br />
        <select className="field" disabled={off} value={spec.pattern} onChange={(e) => void editPart(part.id, { pattern: e.target.value })}>
          {patterns.map((p) => <option key={p} value={p}>{PATTERN_LABEL(p)}</option>)}
        </select></label>
      <p>Density {spec.density.toFixed(2)}
        <Slider.Root className="slider" min={0} max={1} step={0.05} value={[spec.density]} disabled={off} aria-label="Density"
          onValueCommit={([v]) => void editPart(part.id, { density: v })}>
          <Slider.Track className="slider-track"><Slider.Range className="slider-range" /></Slider.Track>
          <Slider.Thumb className="slider-thumb" aria-label="Density" />
        </Slider.Root></p>
      <p>Velocity {spec.velocity[0]}–{spec.velocity[1]}
        <Slider.Root className="slider" min={1} max={127} step={1} value={spec.velocity} disabled={off} aria-label="Velocity range"
          onValueCommit={(v) => void editPart(part.id, { velocity: v })}>
          <Slider.Track className="slider-track"><Slider.Range className="slider-range" /></Slider.Track>
          <Slider.Thumb className="slider-thumb" aria-label="Lowest velocity" />
          <Slider.Thumb className="slider-thumb" aria-label="Highest velocity" />
        </Slider.Root></p>
      <label>Register<br />
        <select className="field" disabled={off} value={spec.register} onChange={(e) => void editPart(part.id, { register: e.target.value })}>
          {REGISTERS.map((r) => <option key={r} value={r}>{REGISTER_LABEL[r]}</option>)}
        </select></label>
      {part.role === 'drums' && (
        <label><br />Fills<br />
          <select className="field" disabled={off} value={spec.fills} onChange={(e) => void editPart(part.id, { fills: e.target.value as Fills })}>
            <option value="none">None</option><option value="end_of_section">End of section</option><option value="every_4_bars">Every 4 bars</option>
          </select></label>
      )}
      <p className="muted">Seed {part.seed} · {part.notes.length} notes</p>
    </aside>
  )
}
