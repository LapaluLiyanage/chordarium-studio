import { useEffect } from 'react'
import { Arrangement } from './components/Arrangement'
import { AssistantPanel } from './components/AssistantPanel'
import { BottomBar } from './components/BottomBar'
import { ChordBoard } from './components/ChordBoard'
import { PasteDialog, SettingsDialog } from './components/Dialogs'
import { Inspector } from './components/Inspector'
import { LiveChord } from './components/LiveChord'
import { SongPanel } from './components/SongPanel'
import { Toasts } from './components/Toasts'
import { TopBar } from './components/TopBar'
import { COPY } from './copy'
import { useStore } from './store'
import { useShortcuts } from './useShortcuts'

export function App() {
  const { init, conn, view, reducedMotion } = useStore()
  useEffect(() => { if (!useStore.getState().api) void init() }, [init])
  useShortcuts()
  return (
    <div className="app" data-reduced={reducedMotion}>
      <div>
        <TopBar />
        {conn === 'down' && <div className="banner" role="alert">{COPY.unreachable}</div>}
        {conn === 'connecting' && <div className="banner" role="status">{COPY.starting}</div>}
      </div>
      {view === 'live' ? <LiveChord /> : view === 'chords' ? <ChordBoard /> : (
        <main className="main"><SongPanel /><div style={{ display: 'grid', gridTemplateRows: '1fr auto', gap: 12, minHeight: 0 }}><Arrangement /></div>
          <div style={{ display: 'grid', gridTemplateRows: 'auto 1fr', gap: 12, minHeight: 0 }}><Inspector /><AssistantPanel /></div></main>
      )}
      <BottomBar />
      <PasteDialog /><SettingsDialog /><SettingsDialog setup /><Toasts />
    </div>
  )
}
