// Full flow against a REAL core: paste -> fix chord -> arrange -> edit -> export.
// Runs only when CHORDARIUM_E2E_URL and CHORDARIUM_E2E_TOKEN are set (see scripts/e2e.sh).
import { describe, expect, it } from 'vitest'
import { CoreApi } from '../api/core'

const url = process.env.CHORDARIUM_E2E_URL, token = process.env.CHORDARIUM_E2E_TOKEN
describe.skipIf(!url || !token)('UI client against real core', () => {
  it('runs the whole flow', async () => {
    const api = new CoreApi({ baseUrl: url!, token: token! })
    expect((await api.health()).status).toBe('ok')
    const song = await api.parse('Key: G\nTempo: 76\n[Chorus]\n| G | Em C | D |\n', 'E2E')
    expect(song.sections[0].bars).toHaveLength(3)
    let snap = await api.snapshot()
    const sections = structuredClone(snap.song!.sections)
    sections[0].bars[0].chords[0].symbol = 'Gmaj7'
    await api.patchSong({ sections })
    await expect(api.patchSong({ sections: (() => { const s = structuredClone(sections); s[0].bars[0].chords[0].symbol = 'Xq'; return s })() })).rejects.toThrow(/not a chord/)
    const sid = sections[0].id
    await api.arrange({ section_ids: [sid], style: 'sinhala_ballad', dynamics: 'soft' })
    snap = await api.snapshot()
    const parts = Object.values(snap.parts)
    expect(parts.map((p) => p.role).sort()).toEqual(['bass', 'drums', 'pad', 'piano'])
    const bass = parts.find((p) => p.role === 'bass')!
    const edited = await api.editPart(bass.id, { density: 0.9 })
    expect(edited.spec.density).toBe(0.9)
    await api.lock(bass.id, true)
    await expect(api.editPart(bass.id, { density: 0.2 })).rejects.toThrow(/locked/i)
    const exp = await api.exportMidi('section', [sid])
    expect(exp.files.length).toBeGreaterThan(0)
  })
})
