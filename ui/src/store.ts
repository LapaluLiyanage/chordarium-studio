import { create } from 'zustand'
import { ApiError, CoreApi } from './api/core'
import { getBridge, type RoleMix, type SyncMode } from './bridge'
import { COPY } from './copy'
import type { AppConfig, ArrangementPlan, Bar, NoteEvent, Part, Role, Snapshot, StyleInfo } from './types'
import { PPQ, ROLES } from './types'

export type Dialog = null | 'paste' | 'setup' | 'settings'
export interface ChatMsg { id: number; kind: 'user' | 'assistant' | 'tool'; text: string; ok?: boolean }
export interface Activity { id: number; text: string; at: number }
export interface Toast { id: number; kind: 'info' | 'error'; text: string }

interface State {
  api: CoreApi | null
  conn: 'connecting' | 'ready' | 'down'
  downSince: number | null
  snap: Snapshot | null
  styles: StyleInfo[]
  config: AppConfig | null
  cubaseLink: boolean
  selectedId: string | null
  lane: Role | null
  inspector: Role | null
  view: 'arranger' | 'live'
  dialog: Dialog
  chat: ChatMsg[]
  thinking: boolean
  activity: Activity[]
  toasts: Toast[]
  mix: Record<Role, RoleMix>
  syncMode: SyncMode
  loop: boolean
  playing: boolean
  saved: boolean
  reducedMotion: boolean
  uiScale: number

  init(api?: CoreApi): Promise<void>
  refresh(): Promise<void>
  toast(text: string, kind?: Toast['kind']): void
  dismissToast(id: number): void
  guard<T>(fn: () => Promise<T>): Promise<T | undefined>
  selectSection(id: string): Promise<void>
  importSheet(text: string, title?: string): Promise<boolean>
  patchChord(sectionId: string, bar: number, slot: number, symbol: string): Promise<boolean>
  editBars(sectionId: string, change: (bars: Bar[], beatsPerBar: number) => void): Promise<boolean>
  newSong(): Promise<void>
  setMeta(patch: Record<string, unknown>): Promise<void>
  arrange(sectionIds: string[], style?: string, dynamics?: string): Promise<void>
  editPart(partId: string, changes: Record<string, unknown>): Promise<void>
  regenerate(partId: string): Promise<void>
  toggleLock(partId: string): Promise<void>
  setNotes(partId: string, notes: NoteEvent[]): Promise<void>
  undo(): Promise<void>
  redo(): Promise<void>
  sendChat(text: string): Promise<void>
  exportMidi(scope: 'part' | 'section' | 'song', ids?: string[]): Promise<void>
  transport(action: string): Promise<void>
  play(): void
  stop(): void
  setLoop(on: boolean): void
  setMix(role: Role, patch: Partial<RoleMix>): void
  setSync(mode: SyncMode): void
  setDialog(d: Dialog): void
  setView(v: 'arranger' | 'live'): void
  setInspector(r: Role | null): void
  setLane(r: Role | null): void
  setConfig(patch: Partial<AppConfig> & { api_key?: string }): Promise<void>
  testProvider(): Promise<{ ok: boolean; detail: string; models: string[] } | undefined>
  setAppearance(p: { reducedMotion?: boolean; uiScale?: number }): void
}

let uid = 1
let closeWs: (() => void) | null = null
let retry: ReturnType<typeof setTimeout> | undefined

export const sectionQuarters = (snap: Snapshot | null, id: string | null): number => {
  const sec = snap?.song?.sections.find((s) => s.id === id)
  return sec ? sec.bars.reduce((t, b) => t + b.chords.reduce((u, c) => u + c.beats, 0), 0) : 16
}

export const useStore = create<State>((set, get) => ({
  api: null, conn: 'connecting', downSince: null, snap: null, styles: [], config: null, cubaseLink: false,
  selectedId: null, lane: null, inspector: null, view: 'arranger', dialog: null,
  chat: [], thinking: false, activity: [], toasts: [], saved: true,
  mix: Object.fromEntries(ROLES.map((r) => [r, { mute: false, solo: false, gain: 0.8 }])) as Record<Role, RoleMix>,
  syncMode: 'free', loop: true, playing: false, reducedMotion: false, uiScale: 100,

  async init(injected) {
    clearTimeout(retry); closeWs?.()
    try {
      const api = injected ?? new CoreApi(await getBridge().getCoreConnection())
      set({ api })
      const h = await api.health()
      set({ conn: 'ready', downSince: null, cubaseLink: h.cubase_remote })
      const [styles, config] = await Promise.all([api.styles(), api.getConfig()])
      set({ styles: styles.styles, config })
      await get().refresh()
      if (!get().snap?.song) set({ dialog: get().config?.provider === 'rules' && !localStorage.getItem('chordarium.setupDone') ? 'setup' : null })
      closeWs = api.connectWs((e) => {
        const t = e.type as string
        if (t === 'session.updated') void get().refresh()
        else if (t === 'part.updated' && e.part) {
          const p = e.part as Part
          set((s) => s.snap ? { snap: { ...s.snap, parts: { ...s.snap.parts, [p.id]: p } } } : s)
        } else if (t === 'activity') set((s) => ({ activity: [{ id: uid++, text: String(e.summary), at: Date.now() }, ...s.activity].slice(0, 30) }))
        else if (t === 'provider.status') void api.getConfig().then((config) => set({ config }))
      }, (up) => set((s) => ({ conn: up ? 'ready' : s.conn === 'ready' ? 'down' : s.conn, downSince: up ? null : s.downSince ?? Date.now() })))
    } catch {
      set((s) => ({ conn: 'down', downSince: s.downSince ?? Date.now() }))
      retry = setTimeout(() => void get().init(injected), 3000)
    }
  },

  async refresh() {
    const api = get().api; if (!api) return
    const snap = await api.snapshot()
    const sel = get().selectedId
    const ids = snap.song?.sections.map((s) => s.id) ?? []
    set({ snap, selectedId: sel && ids.includes(sel) ? sel : snap.selected_section_id ?? ids[0] ?? null, saved: true })
  },

  toast(text, kind = 'info') { set((s) => ({ toasts: [...s.toasts, { id: uid++, kind, text }].slice(-4) })) },
  dismissToast(id) { set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })) },

  async guard(fn) {
    try { set({ saved: false }); const r = await fn(); set({ saved: true }); return r }
    catch (e) { set({ saved: true }); get().toast(e instanceof ApiError || e instanceof Error ? e.message : String(e), 'error'); return undefined }
  },

  async selectSection(id) { set({ selectedId: id }); await get().api?.select(id).catch(() => {}) },

  async importSheet(text, title) {
    const api = get().api; if (!api) return false
    const song = await get().guard(() => api.parse(text, title))
    if (!song) return false
    await get().refresh(); set({ dialog: null })
    return true
  },

  async patchChord(sectionId, bar, slot, symbol) {
    const { api, snap } = get(); if (!api || !snap?.song) return false
    const sections = structuredClone(snap.song.sections)
    const sec = sections.find((s) => s.id === sectionId); if (!sec) return false
    sec.bars[bar].chords[slot].symbol = symbol
    const ok = await get().guard(() => api.patchSong({ sections }))
    if (ok) await get().refresh()
    return !!ok
  },

  async editBars(sectionId, change) {
    const { api, snap } = get(); if (!api || !snap?.song) return false
    const sections = structuredClone(snap.song.sections)
    const sec = sections.find((x) => x.id === sectionId); if (!sec) return false
    change(sec.bars, snap.song.time_signature[0])
    const ok = await get().guard(() => api.patchSong({ sections }))
    if (ok) await get().refresh()
    return !!ok
  },

  async newSong() {
    const api = get().api; if (!api) return
    getBridge().previewStop(); set({ playing: false })
    await get().guard(() => api.newSession())
    await get().refresh()
  },

  async setMeta(patch) {
    const api = get().api; if (!api) return
    await get().guard(() => api.patchSong(patch)); await get().refresh()
  },

  async arrange(sectionIds, style, dynamics) {
    const api = get().api; if (!api) return
    set({ thinking: true })
    await get().guard(() => api.arrange({ section_ids: sectionIds, style, dynamics }))
    set({ thinking: false }); await get().refresh()
  },

  async editPart(partId, changes) {
    const api = get().api; if (!api) return
    const p = await get().guard(() => api.editPart(partId, changes))
    if (p) set((s) => s.snap ? { snap: { ...s.snap, parts: { ...s.snap.parts, [p.id]: p } } } : s)
  },
  async regenerate(partId) {
    const api = get().api; if (!api) return
    const p = await get().guard(() => api.regenerate(partId))
    if (p) set((s) => s.snap ? { snap: { ...s.snap, parts: { ...s.snap.parts, [p.id]: p } } } : s)
  },
  async setNotes(partId, notes) {
    const { api, snap } = get(); const part = snap?.parts[partId]; if (!api || !part) return
    const wasLocked = part.locked
    const ok = await get().guard(() => api.putNotes(partId, notes))
    await get().refresh()   // also when rejected, so the roll snaps back to what the core holds
    if (ok && !wasLocked) get().toast(`${part.role[0].toUpperCase()}${part.role.slice(1)} is now hand-edited and locked, so Re-arrange keeps it. Unlock it to regenerate.`)
  },
  async toggleLock(partId) {
    const { api, snap } = get(); const part = snap?.parts[partId]; if (!api || !part) return
    await get().guard(() => api.lock(partId, !part.locked)); await get().refresh()
  },
  async undo() { const api = get().api; if (api) { await get().guard(() => api.undo()); await get().refresh() } },
  async redo() { const api = get().api; if (api) { await get().guard(() => api.redo()); await get().refresh() } },

  async sendChat(text) {
    const { api, selectedId } = get(); if (!api || !text.trim()) return
    const aid = uid++
    set((s) => ({ chat: [...s.chat, { id: uid++, kind: 'user', text }], thinking: true }))
    try {
      await api.chat(text, selectedId, (ev) => {
        if (ev.type === 'chat.delta') set((s) => {
          const has = s.chat.some((m) => m.id === aid)
          return { chat: has ? s.chat.map((m) => (m.id === aid ? { ...m, text: m.text + ev.text } : m)) : [...s.chat, { id: aid, kind: 'assistant', text: ev.text }] }
        })
        else if (ev.type === 'chat.tool') set((s) => ({ chat: [...s.chat, { id: uid++, kind: 'tool', text: ev.summary, ok: ev.ok }] }))
        else if (ev.type === 'error') get().toast(/limit/i.test(ev.message) ? ev.message : ev.message, 'error')
      })
    } catch (e) { get().toast((e as Error).message, 'error') }
    set({ thinking: false }); await get().refresh()
  },

  async exportMidi(scope, ids) {
    const api = get().api; if (!api) return
    const r = await get().guard(() => api.exportMidi(scope, ids ?? (scope === 'section' && get().selectedId ? [get().selectedId!] : undefined)))
    if (r) {
      getBridge().revealFile(r.files[0])   // show the file in Explorer so it can be dragged into Cubase
      get().toast(`Exported ${r.files.length} MIDI file${r.files.length === 1 ? '' : 's'} to ${r.files[0]}`)
    }
  },
  async transport(action) {
    const api = get().api; if (!api) return
    try { await api.remote(action) } catch { get().toast(COPY.cubaseMissing) }
  },

  play() {
    const { snap, selectedId } = get(); if (!selectedId) return
    getBridge().previewPlay(selectedId, sectionQuarters(snap, selectedId), snap?.song?.tempo_bpm ?? 90)
    set({ playing: true })
  },
  stop() { getBridge().previewStop(); set({ playing: false }) },
  setLoop(on) { getBridge().setLoop(on); set({ loop: on }) },
  setMix(role, patch) {
    const m = { ...get().mix[role], ...patch }; getBridge().setRoleMix(role, m)
    set((s) => ({ mix: { ...s.mix, [role]: m } }))
  },
  setSync(mode) { getBridge().setSyncMode(mode); set({ syncMode: mode }) },
  setDialog(d) { set({ dialog: d }) },
  setView(v) { set({ view: v }) },
  setInspector(r) { set({ inspector: r }) },
  setLane(r) { set({ lane: r }) },

  async setConfig(patch) {
    const api = get().api; if (!api) return
    const config = await get().guard(() => api.putConfig(patch)); if (config) set({ config })
  },
  async testProvider() { const api = get().api; return api ? get().guard(() => api.testProvider()) : undefined },
  setAppearance(p) {
    set((s) => ({ reducedMotion: p.reducedMotion ?? s.reducedMotion, uiScale: p.uiScale ?? s.uiScale }))
    if (p.uiScale) document.documentElement.style.setProperty('--ui-scale', String(p.uiScale / 100))
  },
}))

export const partsFor = (snap: Snapshot | null, sectionId: string | null): Part[] =>
  snap && sectionId ? Object.values(snap.parts).filter((p) => p.section_id === sectionId).sort((a, b) => ROLES.indexOf(a.role) - ROLES.indexOf(b.role)) : []
export const planFor = (snap: Snapshot | null, id: string | null): ArrangementPlan | undefined => (snap && id ? snap.plans[id] : undefined)
export const ticksToBars = (ticks: number, ts: [number, number]) => ticks / (PPQ * (ts[0] * 4 / ts[1]))
