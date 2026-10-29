import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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

beforeEach(() => { localStorage.setItem('chordarium.setupDone', '1'); setBridge(createMockBridge()); useStore.setState({ snap: null, dialog: null, chat: [], toasts: [], view: 'arranger', playing: false }) })

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
    await userEvent.click(await screen.findByRole('button', { name: 'Chords' }))
    await userEvent.click(await screen.findByLabelText('Bar 2 chord Em'))
    const input = screen.getByLabelText('Chord symbol')
    await userEvent.clear(input); await userEvent.type(input, 'Am{Enter}')
    await waitFor(() => expect(patchSong).toHaveBeenCalled())
    const sections = (patchSong.mock.calls[0] as unknown as [{ sections: { bars: { chords: { symbol: string }[] }[] }[] }])[0].sections
    expect(sections[0].bars[1].chords[0].symbol).toBe('Am')
  })
  it('adds, splits and deletes bars from the Chords view', async () => {
    const patchSong = vi.fn(async () => ({}))
    await useStore.getState().init(fakeApi({ patchSong }))
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'Chords' }))
    type Sent = [{ sections: { bars: { chords: { symbol: string; beats: number }[] }[] }[] }]
    const last = () => (patchSong.mock.calls.at(-1) as unknown as Sent)[0].sections[0].bars

    await userEvent.click(await screen.findByRole('button', { name: 'Add a bar to Chorus 1' }))
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
  describe('piano roll editing', () => {
    // 8 quarters = 3840 ticks over 384 px, so 1 px = 10 ticks. One note: pitch 60, start 0, 480 long (x 0..48), velocity 50.
    // Pitches 60..71 over a 64 px canvas: row height 4.67 px, pitch 60 sits at y 55..60.
    const setup = async () => {
      const putNotes = vi.fn(async () => ({}))
      await useStore.getState().init(fakeApi({ putNotes }))
      render(<App />)
      const roll = await screen.findByRole('img', { name: /piano notes: 1/ })
      roll.getBoundingClientRect = () => ({ left: 0, top: 0, width: 384, height: 64, right: 384, bottom: 64, x: 0, y: 0, toJSON: () => ({}) })
      type Sent = [string, { pitch: number; start: number; duration: number; velocity: number }[]]
      return { roll, putNotes, sent: (n: number) => putNotes.mock.calls[n] as unknown as Sent }
    }

    it('adds a note by clicking empty space', async () => {
      const { roll, putNotes, sent } = await setup()
      fireEvent.pointerDown(roll, { clientX: 48, clientY: 50 })   // tick 480, two rows up = pitch 62
      await waitFor(() => expect(putNotes).toHaveBeenCalledTimes(1))
      expect(sent(0)[0]).toBe('p_piano')
      expect(sent(0)[1]).toHaveLength(2)
      expect(sent(0)[1][1]).toMatchObject({ pitch: 62, start: 480, duration: 240 })
    })

    it('moves a note by dragging it, snapped to the grid', async () => {
      const { roll, putNotes, sent } = await setup()
      fireEvent.pointerDown(roll, { clientX: 10, clientY: 58 })
      fireEvent.pointerMove(roll, { clientX: 58, clientY: 49 })   // +480 ticks, two rows up
      fireEvent.pointerUp(roll, { clientX: 58, clientY: 49 })
      await waitFor(() => expect(putNotes).toHaveBeenCalledTimes(1))
      expect(sent(0)[1]).toHaveLength(1)
      expect(sent(0)[1][0]).toMatchObject({ pitch: 62, start: 480, duration: 480 })
    })

    it('resizes a note by dragging its right end', async () => {
      const { roll, putNotes, sent } = await setup()
      fireEvent.pointerDown(roll, { clientX: 45, clientY: 58 })   // within 7 px of the note end (x = 48)
      fireEvent.pointerMove(roll, { clientX: 96, clientY: 58 })
      fireEvent.pointerUp(roll, { clientX: 96, clientY: 58 })
      await waitFor(() => expect(putNotes).toHaveBeenCalledTimes(1))
      expect(sent(0)[1][0]).toMatchObject({ pitch: 60, start: 0, duration: 960 })
    })

    it('selects on click without changing anything, then edits velocity from the keyboard', async () => {
      const { roll, putNotes, sent } = await setup()
      fireEvent.pointerDown(roll, { clientX: 10, clientY: 58 })
      fireEvent.pointerUp(roll, { clientX: 10, clientY: 58 })
      expect(putNotes).not.toHaveBeenCalled()   // a plain click only selects
      fireEvent.keyDown(roll, { key: 'ArrowUp' })
      await waitFor(() => expect(putNotes).toHaveBeenCalledTimes(1))
      expect(sent(0)[1][0].velocity).toBe(55)
    })

    it('deletes a note with a double-click', async () => {
      const { roll, putNotes, sent } = await setup()
      fireEvent.doubleClick(roll, { clientX: 10, clientY: 58 })
      await waitFor(() => expect(putNotes).toHaveBeenCalledTimes(1))
      expect(sent(0)[1]).toHaveLength(0)
    })
  })
  describe('chord board', () => {
    const setup = async (extra: Record<string, unknown> = {}) => {
      const patchSong = vi.fn(async () => ({}))
      await useStore.getState().init(fakeApi({ patchSong, ...extra }))
      render(<App />)
      await userEvent.click(await screen.findByRole('button', { name: 'Chords' }))
      type Sent = [{ key?: string; sections: { bars: { chords: { symbol: string }[] }[] }[] }]
      return { patchSong, sent: (n = 0) => (patchSong.mock.calls[n] as unknown as Sent)[0] }
    }

    it('shows every section as bar cards with a bar range', async () => {
      await setup()
      expect(await screen.findByLabelText('Chord board')).toBeInTheDocument()
      expect(screen.getByText('BARS 1–2')).toBeInTheDocument()
      expect(screen.getByLabelText('Bar 1 chord G')).toBeInTheDocument()
      expect(screen.getByLabelText('Bar 2 chord Em')).toBeInTheDocument()
    })

    it('changes bars per row and remembers it', async () => {
      await setup()
      await userEvent.click(screen.getByRole('button', { name: '8 / ROW' }))
      expect(screen.getByRole('button', { name: '8 / ROW' })).toHaveAttribute('aria-pressed', 'true')
      expect(localStorage.getItem('chordarium.perRow')).toBe('8')
    })

    it('transposes every chord and the key', async () => {
      const { patchSong, sent } = await setup()
      await userEvent.click(screen.getByRole('button', { name: 'Transpose up one semitone' }))
      await waitFor(() => expect(patchSong).toHaveBeenCalledTimes(1))
      expect(sent().key).toBe('Ab')   // G major up a semitone is Ab major, spelled with flats
      expect(sent().sections[0].bars.map((b) => b.chords[0].symbol)).toEqual(['Ab', 'Fm'])   // G -> Ab, Em -> Fm
      expect(await screen.findByText('TRANSPOSE +1')).toBeInTheDocument()
    })

    it('lights up the bar and chord that is playing, and shows it in the toolbar', async () => {
      const { patchSong } = await setup()
      expect(patchSong).not.toHaveBeenCalled()
      expect(document.querySelector('.bar.now')).toBeNull()   // nothing is lit before Play
      await userEvent.click(screen.getByRole('button', { name: 'Play selected section' }))
      await waitFor(() => expect(document.querySelector('.bar.now')).not.toBeNull())
      expect(document.querySelector('.bar.now .slot.active')).not.toBeNull()
      expect(await screen.findByRole('status', { name: /Now playing G/ })).toBeInTheDocument()   // first beat of the section: G
      await userEvent.click(screen.getAllByRole('button', { name: 'Stop preview' })[0])   // the board and the bottom bar both have one
      await waitFor(() => expect(document.querySelector('.bar.now')).toBeNull())
    })

    it('simplifies chords to triads', async () => {
      const complex = () => ({ ...snap(), song: { ...snap().song!, sections: [{ id: 's1', name: 'Chorus 1', kind: 'chorus' as const, lyrics: null, bars: [{ chords: [{ symbol: 'Gmaj7/B', beats: 4 }] }, { chords: [{ symbol: 'Em7', beats: 4 }] }] }] } })
      const { patchSong, sent } = await setup({ snapshot: async () => complex() })
      await userEvent.click(screen.getByRole('button', { name: 'SIMPLIFY' }))
      await waitFor(() => expect(patchSong).toHaveBeenCalledTimes(1))
      expect(sent().sections[0].bars.map((b) => b.chords[0].symbol)).toEqual(['G', 'Em'])
    })
  })

  it('changes the window size from the top bar', async () => {
    await useStore.getState().init(fakeApi())
    render(<App />)
    const before = useStore.getState().uiScale
    await userEvent.click(await screen.findByRole('button', { name: 'Make everything larger' }))
    expect(useStore.getState().uiScale).toBe(before + 10)
    expect(localStorage.getItem('chordarium.uiScale.v2')).toBe(String(before + 10))
    await userEvent.click(screen.getByRole('button', { name: /Size \d+ percent/ }))
    expect(useStore.getState().uiScale).toBe(100)
  })

  it('keeps the Arranger chord grid read-only and points to the Chords view', async () => {
    await useStore.getState().init(fakeApi())
    render(<App />)
    await screen.findByLabelText('Bar 1 chord G')
    expect(screen.queryByRole('button', { name: 'Bar 1 chord G' })).toBeNull()      // shown, not clickable
    expect(screen.queryByLabelText('Delete bar 1')).toBeNull()
    expect(screen.queryByLabelText('Add a chord to bar 1')).toBeNull()
    expect(screen.queryByRole('button', { name: 'Add bar' })).toBeNull()
  })

  it('starts a file drag after a press-and-drag on a lane, but not on a plain click', async () => {
    const startFileDrag = vi.fn()
    setBridge({ ...createMockBridge(), startFileDrag })
    await useStore.getState().init(fakeApi())
    render(<App />)
    const head = (await screen.findByLabelText('Inspect Piano')).closest('.head') as HTMLElement
    fireEvent.pointerDown(head, { button: 0, clientX: 10, clientY: 10 })
    fireEvent.pointerUp(window)
    expect(startFileDrag).not.toHaveBeenCalled()                     // a click only inspects the lane
    fireEvent.pointerDown(head, { button: 0, clientX: 10, clientY: 10 })
    fireEvent.pointerMove(window, { buttons: 1, clientX: 30, clientY: 12 })
    expect(startFileDrag).toHaveBeenCalledWith('p_piano')
    fireEvent.pointerMove(window, { buttons: 1, clientX: 60, clientY: 12 })
    expect(startFileDrag).toHaveBeenCalledTimes(1)                   // one drag per press
  })

  it('drags the whole section from the Drag all button', async () => {
    const startFileDrag = vi.fn()
    setBridge({ ...createMockBridge(), startFileDrag })
    await useStore.getState().init(fakeApi())
    render(<App />)
    const all = await screen.findByRole('button', { name: 'Drag all tracks to Cubase' })
    fireEvent.pointerDown(all, { button: 0, clientX: 5, clientY: 5 })
    fireEvent.pointerMove(window, { buttons: 1, clientX: 40, clientY: 40 })
    expect(startFileDrag).toHaveBeenCalledWith('section:s1')
  })

  it('shows an error toast when the core rejects a chord', async () => {
    await useStore.getState().init(fakeApi({ patchSong: async () => { throw new Error("Chorus 1, bar 1: 'Xq' is not a chord I know.") } }))
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'Chords' }))
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
