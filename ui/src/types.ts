// Mirrors engine/models.py (spec section 6). Ticks, PPQ = 480.
export const PPQ = 480
export type Role = 'piano' | 'bass' | 'pad' | 'drums'
export type Register = 'low' | 'mid_low' | 'mid' | 'mid_high' | 'high'
export type Fills = 'none' | 'end_of_section' | 'every_4_bars'
export type Dynamics = 'soft' | 'medium' | 'loud'
export type SectionKind = 'intro' | 'verse' | 'pre_chorus' | 'chorus' | 'bridge' | 'interlude' | 'solo' | 'outro' | 'other'

export interface ChordSlot { symbol: string; beats: number }
export interface Bar { chords: ChordSlot[] }
export interface Section { id: string; name: string; kind: SectionKind; bars: Bar[]; lyrics: (string | null)[] | null }
export interface Song {
  id: string; title: string; key: string | null; mode: 'major' | 'minor'; tempo_bpm: number
  time_signature: [number, number]; capo: number; language: 'en' | 'si'; sections: Section[]; warnings: string[]
}
export interface PartSpec {
  role: Role; pattern: string; density: number; velocity: [number, number]; register: Register
  instrument: string | null; fills: Fills; seed: number | null; locked: boolean; variation: number
}
export interface ArrangementPlan { section_id: string; style: string; feel: string; dynamics: Dynamics; parts: PartSpec[]; notes: string }
export interface NoteEvent { pitch: number; start: number; duration: number; velocity: number }
export interface Part {
  id: string; section_id: string; role: Role; channel: number; spec: PartSpec; seed: number; locked: boolean
  notes: NoteEvent[]; ccs: { cc: number; start: number; value: number }[]
}
export interface Snapshot {
  id: string; song: Song | null; plans: Record<string, ArrangementPlan>; parts: Record<string, Part>
  selected_section_id: string | null
}
export interface StyleInfo {
  id: string; name: string; time_signatures: [number, number][]; tempo_range: [number, number]
  patterns: Record<Role, string[]>; defaults: Record<string, Record<string, unknown>>
}
export interface AppConfig { provider: string; model: string; base_url: string; port: number; cubase_port_name: string; has_key?: boolean }
export type ChatEvent =
  | { type: 'chat.delta'; text: string }
  | { type: 'chat.tool'; name: string; ok: boolean; summary: string }
  | { type: 'chat.done' }
  | { type: 'error'; message: string }

export const ROLES: Role[] = ['piano', 'bass', 'pad', 'drums']
export const REGISTERS: Register[] = ['low', 'mid_low', 'mid', 'mid_high', 'high']
