import { describe, expect, it } from 'vitest'
import { locate } from '../nowPlaying'
import type { Section } from '../types'

// 3 bars of 4 beats: | G | Em C (2 beats each) | D |
const sec: Section = { id: 's', name: 'Chorus', kind: 'chorus', lyrics: null, bars: [
  { chords: [{ symbol: 'G', beats: 4 }] },
  { chords: [{ symbol: 'Em', beats: 2 }, { symbol: 'C', beats: 2 }] },
  { chords: [{ symbol: 'D', beats: 4 }] },
] }

describe('locate', () => {
  it('finds the chord sounding at a position', () => {
    expect(locate(sec, 0)).toEqual({ bar: 0, slot: 0, symbol: 'G' })
    expect(locate(sec, 3.9)).toEqual({ bar: 0, slot: 0, symbol: 'G' })
    expect(locate(sec, 4)).toEqual({ bar: 1, slot: 0, symbol: 'Em' })
    expect(locate(sec, 5.99)).toEqual({ bar: 1, slot: 0, symbol: 'Em' })
    expect(locate(sec, 6)).toEqual({ bar: 1, slot: 1, symbol: 'C' })
    expect(locate(sec, 11.5)).toEqual({ bar: 2, slot: 0, symbol: 'D' })
  })
  it('loops past the end of the section and handles negative positions', () => {
    expect(locate(sec, 12)).toEqual({ bar: 0, slot: 0, symbol: 'G' })
    expect(locate(sec, 25)).toEqual({ bar: 0, slot: 0, symbol: 'G' })
    expect(locate(sec, -1)).toEqual({ bar: 2, slot: 0, symbol: 'D' })
  })
  it('returns null for a missing or empty section', () => {
    expect(locate(undefined, 1)).toBeNull()
    expect(locate({ ...sec, bars: [] }, 1)).toBeNull()
  })
})
