import type { CoreConn } from '../api/core'
import type { Role } from '../types'
import type { Bridge, DragRect, HostInfo, Position, RoleMix, SyncMode } from './index'

/**
 * JUCE 8 native bridge. [VERIFY] against the JS helper that ships in juce_gui_extra (milestone M4):
 * names below follow its `getNativeFunction(name)` + `window.__JUCE__.backend` event API.
 */
interface JuceBackend { addEventListener(id: string, cb: (payload: unknown) => void): [string, number]; removeEventListener(t: [string, number]): void }
declare global { interface Window { __JUCE__?: { backend: JuceBackend; initialisationData?: Record<string, unknown> } } }

let nextId = 0
function native<T = unknown>(name: string) {
  // Same wire protocol as JUCE's helper: emit "__juce__invoke", wait for "__juce__complete" with the same resultId.
  return (...params: unknown[]): Promise<T> => new Promise<T>((resolve) => {
    const j = window.__JUCE__!; const resultId = nextId++
    const tok = j.backend.addEventListener('__juce__complete', (p) => {
      const r = p as { promiseId: number; result: T }
      if (r.promiseId === resultId) { j.backend.removeEventListener(tok); resolve(r.result) }
    })
    ;(j.backend as unknown as { emitEvent(id: string, p: unknown): void }).emitEvent('__juce__invoke', { name, params, resultId })
  })
}

export function createJuceBridge(): Bridge {
  const fn = (n: string) => native(n)
  let pos: Position = { playing: false, quarters: 0, bpm: 90 }
  const meters = new Set<(l: Record<Role, number>) => void>()
  const drags = new Set<(id: string) => void>()
  const b = window.__JUCE__!.backend
  b.addEventListener('transport', (p) => { pos = p as Position })
  b.addEventListener('meter', (p) => meters.forEach((cb) => cb(p as Record<Role, number>)))
  b.addEventListener('dragDone', (p) => drags.forEach((cb) => cb(String(p))))
  return {
    kind: 'juce',
    getCoreConnection: () => fn('getCoreConnection')() as Promise<CoreConn>,
    previewPlay: (s, q, bpm) => void fn('previewPlay')(s, q, bpm),
    previewStop: () => void fn('previewStop')(),
    setLoop: (on) => void fn('setLoop')(on),
    setRoleMix: (r: Role, m: RoleMix) => void fn('setRoleMix')(r, m),
    setSyncMode: (m: SyncMode) => void fn('setSyncMode')(m),
    reportDragRects: (r: DragRect[]) => void fn('reportDragRects')(r),
    getHostInfo: () => fn('getHostInfo')() as Promise<HostInfo>,
    position: () => pos,
    onMeter: (cb) => { meters.add(cb); return () => meters.delete(cb) },
    onDragDone: (cb) => { drags.add(cb); return () => drags.delete(cb) },
  }
}
