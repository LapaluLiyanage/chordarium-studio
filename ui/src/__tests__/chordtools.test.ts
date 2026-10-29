import { describe, expect, it } from 'vitest'
import { keyUsesFlats, shiftNote, simplifyChord, transposeChord } from '../chordtools'

describe('transposeChord', () => {
  it('moves roots and slash basses together', () => {
    expect(transposeChord('B', 1, false)).toBe('C')
    expect(transposeChord('F#m7/C#', 2, false)).toBe('G#m7/D#')
    expect(transposeChord('Emaj7', -4, false)).toBe('Cmaj7')
  })
  it('wraps around the octave in both directions', () => {
    expect(transposeChord('B', 1, false)).toBe('C')
    expect(transposeChord('C', -1, false)).toBe('B')
    expect(transposeChord('A', 12, false)).toBe('A')
  })
  it('spells with flats when asked and leaves N.C. and unreadable text alone', () => {
    expect(transposeChord('E', 1, true)).toBe('F')
    expect(transposeChord('A', 1, true)).toBe('Bb')
    expect(transposeChord('N.C.', 3, false)).toBe('N.C.')
    expect(transposeChord('??', 3, false)).toBe('??')
  })
})

describe('keys', () => {
  it('knows which keys use flats, including relative minors', () => {
    expect(keyUsesFlats('F')).toBe(true)
    expect(keyUsesFlats('G')).toBe(false)
    expect(keyUsesFlats('D', 'minor')).toBe(true)    // relative major is F
    expect(keyUsesFlats('E', 'minor')).toBe(false)   // relative major is G
  })
  it('shifts note names', () => {
    expect(shiftNote('Bb', 2, false)).toBe('C')
    expect(shiftNote('H', 2, false)).toBe('H')
  })
})

describe('simplifyChord', () => {
  it('reduces to the triad and drops the slash bass', () => {
    expect(simplifyChord('Emaj7')).toBe('E')
    expect(simplifyChord('G#m7')).toBe('G#m')
    expect(simplifyChord('F#7/C#')).toBe('F#')
    expect(simplifyChord('B/F#')).toBe('B')
    expect(simplifyChord('Bm7b5')).toBe('Bdim')
    expect(simplifyChord('Csus4')).toBe('Csus4')
    expect(simplifyChord('N.C.')).toBe('N.C.')
  })
})
