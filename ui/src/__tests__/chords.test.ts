import { describe, expect, it } from 'vitest'
import { chordSuggestions, splitChord } from '../chords'

describe('splitChord', () => {
  it('splits root/quality/extension/bass', () => {
    expect(splitChord('Em7')).toEqual({ root: 'E', quality: 'm', ext: '7', bass: '' })
    expect(splitChord('Bbmaj7/D')).toEqual({ root: 'Bb', quality: '', ext: 'maj7', bass: 'D' })
    expect(splitChord('F#sus4')).toEqual({ root: 'F#', quality: 'sus4', ext: '', bass: '' })
    expect(splitChord('N.C.').root).toBe('N.C.')
  })
})
describe('chordSuggestions', () => {
  it('suggests suffixes for a root', () => {
    const s = chordSuggestions('c')
    expect(s).toContain('C') ; expect(s).toContain('Cm7')
    expect(chordSuggestions('zz')).toEqual([])
  })
})
