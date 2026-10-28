export interface ChordParts { root: string; quality: string; ext: string; bass: string }
/** Split a canonical chord symbol for Chordarium's chord style (.cs): small quality, raised extension, teal slash bass. */
export function splitChord(symbol: string): ChordParts {
  if (symbol === 'N.C.') return { root: 'N.C.', quality: '', ext: '', bass: '' }
  const m = /^([A-G][#b]?)(.*?)(?:\/([A-G][#b]?))?$/.exec(symbol)
  if (!m) return { root: symbol, quality: '', ext: '', bass: '' }
  const [, root, rest, bass] = m
  let quality = ''; let ext = rest
  if (/^m(?!aj)/.test(rest)) { quality = 'm'; ext = rest.slice(1) }
  else { const q = /^(dim|aug|sus2|sus4)/.exec(rest); if (q) { quality = q[1]; ext = rest.slice(q[1].length) } }
  return { root, quality, ext, bass: bass ?? '' }
}
export function chordText(symbol: string): string { return symbol }
export const KEYS = ['C', 'C#', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
export const TIME_SIGNATURES: [number, number][] = [[4, 4], [3, 4], [6, 8], [12, 8]]
export const CHORD_SUFFIXES = ['', 'm', '7', 'maj7', 'm7', 'sus2', 'sus4', 'dim', 'aug', 'add9', '6', 'm7b5', '9', '13']
export function chordSuggestions(input: string): string[] {
  const raw = input.trim(); const m = /^([A-Ga-g][#b]?)/.exec(raw); if (!m) return []
  const root = m[1][0].toUpperCase() + m[1].slice(1)
  const typed = root + raw.slice(m[1].length)
  return CHORD_SUFFIXES.map((s) => root + s).filter((c) => c.startsWith(typed)).slice(0, 8)
}
