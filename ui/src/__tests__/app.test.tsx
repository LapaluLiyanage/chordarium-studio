import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from '../App'
import { setBridge } from '../bridge'
import { createMockBridge } from '../bridge/mock'
import { useStore } from '../store'
import type { CoreApi } from '../api/core'
import type { Part, Snapshot } from '../types'

const part = (role: Part['role']): Part => ({
  id: `p_${role}`, section_id: 's1', role, channel: 1, seed: 7, locked: false, ccs: [],
  spec: { role, pattern: 'block', density: 0.4, velocity: [40, 60], register: 'mid', instrument: null, fills: 'none', seed: 7, locked: false, variation: 0 },
  notes: [{ pitch: 60, start: 0, duration: 480, velocity: 50 }],
})
const snap = (): Snapshot => ({
  id: 'x', selected_section_id: 's1', plans: {}, parts: { p_piano: part('piano') },
  song: { id: 'x', title: 'Demo', key: 'G', mode: 'major', tempo_bpm: 80, time_signature: [4, 4], capo: 0, language: 'en', warnings: [],
    sections: [{ id: 's1', name: 'Chorus 1', kind: 'chorus', lyrics: null, bars: [{ chords: [{ symbol: 'G', beats: 4 }] }, { chords: [{ symbol: 'Em', beats: 4 }] }] }] },
})

function fakeApi(over: Record<string, unknown> = {}) {
  return {
    health: async () => ({ status: 'ok', version: '0.1.0', provider: 'rules', cubase_remote: false }),
    styles: async () => ({ styles: [{ id: 'pop_4_4', name: 'Pop', time_signatures: [[4, 4]], tempo_range: [80, 120], patterns: { piano: ['block'], bass: [], pad: [], drums: [] }, defaults: {} }] }),
    getConfig: async () => ({ provider: 'rules', model: '', base_url: '', port: 47811, cubase_port_name: 'Chordarium Remote' }),
    snapshot: async () => snap(),
    select: async () => ({}),
    connectWs: () => () => {},
    ...over,
  } as unknown as CoreApi
}

beforeEach(() => { localStorage.setItem('chordarium.setupDone', '1'); setBridge(createMockBridge()); useStore.setState({ snap: null, dialog: null, chat: [], toasts: [] }) })

describe('App', () => {
  it('shows the empty state when there is no song', async () => {
    await useStore.getState().init(fakeApi({ snapshot: async () => ({ id: 'x', song: null, plans: {}, parts: {}, selected_section_id: null }) }))
    render(<App />)
    expect(await screen.findAllByText(/Paste a chord sheet/)).not.toHaveLength(0)
  })
  it('renders chord grid and parts for a loaded song', async () => {
    await useStore.getState().init(fakeApi())
    render(<App />)
    expect(await screen.findByLabelText('Bar 1 chord G')).toBeInTheDocument()
    expect(screen.getByLabelText('Inspect Piano')).toBeInTheDocument()
  })
  it('edits a chord via patchSong', async () => {
    const patchSong = vi.fn(async () => ({}))
    await useStore.getState().init(fakeApi({ patchSong }))
    render(<App />)
    await userEvent.click(await screen.findByLabelText('Bar 2 chord Em'))
    const input = screen.getByLabelText('Chord symbol')
    await userEvent.clear(input); await userEvent.type(input, 'Am{Enter}')
    await waitFor(() => expect(patchSong).toHaveBeenCalled())
    const sections = (patchSong.mock.calls[0] as unknown as [{ sections: { bars: { chords: { symbol: string }[] }[] }[] }])[0].sections
    expect(sections[0].bars[1].chords[0].symbol).toBe('Am')
  })
  it('adds, splits and deletes bars from the chord grid', async () => {
    const patchSong = vi.fn(async () => ({}))
    await useStore.getState().init(fakeApi({ patchSong }))
    render(<App />)
    type Sent = [{ sections: { bars: { chords: { symbol: string; beats: number }[] }[] }[] }]
    const last = () => (patchSong.mock.calls.at(-1) as unknown as Sent)[0].sections[0].bars

    await userEvent.click(await screen.findByRole('button', { name: 'Add bar' }))
    await waitFor(() => expect(patchSong).toHaveBeenCalledTimes(1))
    expect(last()).toHaveLength(3)
    expect(last()[2].chords).toEqual([{ symbol: 'Em', beats: 4 }])   // repeats the last chord for a full 4/4 bar

    await userEvent.click(screen.getByLabelText('Add a chord to bar 1', { selector: 'button' }))
    await waitFor(() => expect(patchSong).toHaveBeenCalledTimes(2))
    expect(last()[0].chords).toEqual([{ symbol: 'G', beats: 2 }, { symbol: 'G', beats: 2 }])   // beats share the bar evenly

    await userEvent.click(screen.getByLabelText('Delete bar 2', { selector: 'button' }))
    await waitFor(() => expect(patchSong).toHaveBeenCalledTimes(3))
    expect(last()).toHaveLength(1)
  })
  it('shows an error toast when the core rejects a chord', async () => {
    await useStore.getState().init(fakeApi({ patchSong: async () => { throw new Error("Chorus 1, bar 1: 'Xq' is not a chord I know.") } }))
    render(<App />)
    await userEvent.click(await screen.findByLabelText('Bar 1 chord G'))
    await userEvent.type(screen.getByLabelText('Chord symbol'), 'q{Enter}')
    expect(await screen.findByText(/not a chord I know/)).toBeInTheDocument()
  })
  it('shows the unreachable banner when the core is down', async () => {
    useStore.setState({ conn: 'down' })
    render(<App />)
    expect(screen.getByRole('alert')).toHaveTextContent(/Can't reach the engine/)
  })
})
