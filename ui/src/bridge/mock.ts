import type { CoreConn } from '../api/core'
import type { Role } from '../types'
import type { Bridge, DragRect, Position, RoleMix, SyncMode } from './index'

/** Browser dev-mode bridge: simulates transport, meters and playback. No native calls. */
export function createMockBridge(now: () => number = () => performance.now()): Bridge {
  let playing = false; let start = 0; let len = 16; let bpm = 90; let loop = true
  const mix: Record<string, RoleMix> = {}
  const meterCbs = new Set<(l: Record<Role, number>) => void>()
  let meterTimer: ReturnType<typeof setInterval> | undefined
  const stopMeters = () => { if (meterTimer) clearInterval(meterTimer); meterTimer = undefined }
  return {
    kind: 'mock',
    async getCoreConnection(): Promise<CoreConn> {
      const q = typeof location !== 'undefined' ? new URLSearchParams(location.search) : new URLSearchParams()
      const token = q.get('token') ?? safeGet('chordarium.token') ?? ''
      if (q.get('token')) safeSet('chordarium.token', token)
      return { baseUrl: `http://127.0.0.1:${q.get('port') ?? 47811}`, token }
    },
    previewPlay(_s, lengthQuarters, b) {
      playing = true; start = now(); len = Math.max(1, lengthQuarters); bpm = b
      stopMeters()
      meterTimer = setInterval(() => {  // <= 30 fps, only while playing
        const l = { piano: rnd(), bass: rnd(), pad: rnd() * .6, drums: rnd() } as Record<Role, number>
        meterCbs.forEach((cb) => cb(l))
      }, 40)
    },
    previewStop() { playing = false; stopMeters() },
    setLoop(on) { loop = on },
    setBuiltInSound(_on: boolean) {},
    setRoleMix(role, m) { mix[role] = m },
    setSyncMode(_m: SyncMode) {},
    reportDragRects(_r: DragRect[]) {},
    revealFile(_p: string) {},
    startFileDrag(_id: string) {},
    async getHostInfo() { return { host: 'Browser (dev mode)', sampleRate: 48000, bpm } },
    position(): Position {
      if (!playing) return { playing: false, quarters: 0, bpm }
      let q = ((now() - start) / 60000) * bpm
      if (q >= len) { if (loop) q %= len; else { playing = false; stopMeters(); q = 0 } }
      return { playing, quarters: q, bpm }
    },
    onMeter(cb) { meterCbs.add(cb); return () => meterCbs.delete(cb) },
    onDragDone() { return () => {} },
  }
}
const rnd = () => 0.25 + Math.random() * 0.6
function safeGet(k: string) { try { return localStorage.getItem(k) } catch { return null } }
function safeSet(k: string, v: string) { try { localStorage.setItem(k, v) } catch { /* private mode */ } }
