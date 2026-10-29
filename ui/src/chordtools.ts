import { splitChord } from './chords'

const SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
const FLAT = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
const PC: Record<string, number> = { C: 0, 'C#': 1, Db: 1, D: 2, 'D#': 3, Eb: 3, E: 4, F: 5, 'F#': 6, Gb: 6, G: 7, 'G#': 8, Ab: 8, A: 9, 'A#': 10, Bb: 10, B: 11 }
const FLAT_MAJOR_KEYS = new Set([1, 3, 5, 6, 8, 10])   // Db Eb F Gb Ab Bb

const mod12 = (n: number) => ((n % 12) + 12) % 12

/** Move one note name by `semitones`, spelled with flats or sharps. Unknown names are returned unchanged. */
export function shiftNote(note: string, semitones: number, flats: boolean): string {
  const pc = PC[note]
  return pc === undefined ? note : (flats ? FLAT : SHARP)[mod12(pc + semitones)]
}

/** Whether a key is conventionally spelled with flats. `mode` decides how a minor key maps to its relative major. */
export function keyUsesFlats(root: string, mode: 'major' | 'minor' | string = 'major'): boolean {
  const pc = PC[root]
  if (pc === undefined) return false
  return FLAT_MAJOR_KEYS.has(mode === 'minor' ? mod12(pc + 3) : pc)
}

/** Transpose a chord symbol such as `F#m7/C#`: root and slash bass both move. `N.C.` and unreadable symbols are kept. */
export function transposeChord(symbol: string, semitones: number, flats: boolean): string {
  const m = /^([A-G][#b]?)(.*?)(?:\/([A-G][#b]?))?$/.exec(symbol)
  if (!m || symbol === 'N.C.') return symbol
  const [, root, rest, bass] = m
  return `${shiftNote(root, semitones, flats)}${rest}${bass ? `/${shiftNote(bass, semitones, flats)}` : ''}`
}

/** Reduce a chord to its triad: keep root and major/minor/dim/aug/sus, drop sevenths, extensions and slash bass. */
export function simplifyChord(symbol: string): string {
  if (symbol === 'N.C.') return symbol
  const p = splitChord(symbol)
  if (p.quality === 'm' && /^7b5/.test(p.ext)) return `${p.root}dim`
  return `${p.root}${p.quality}`
}
