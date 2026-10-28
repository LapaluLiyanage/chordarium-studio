import { useEffect } from 'react'
import { useStore } from './store'

/** Space = play/stop, Ctrl+Z / Ctrl+Shift+Z = undo/redo. Ignored while typing. */
export function useShortcuts() {
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement
      if (/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) || t.isContentEditable) return
      const s = useStore.getState()
      if (e.code === 'Space') { e.preventDefault(); s.playing ? s.stop() : s.play() }
      else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') { e.preventDefault(); void (e.shiftKey ? s.redo() : s.undo()) }
    }
    window.addEventListener('keydown', h); return () => window.removeEventListener('keydown', h)
  }, [])
}
