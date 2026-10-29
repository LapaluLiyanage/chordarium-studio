import type { PointerEvent as ReactPointerEvent } from 'react'
import { getBridge } from './bridge'

const THRESHOLD_PX = 6

/**
 * Pointer handlers that turn "press and drag" on an element into an operating-system file drag.
 * The plugin cannot overlay native handles on a web view, so the page starts the drag itself: after the pointer
 * has moved a few pixels with the button still held, it asks the plugin to export the file and begin the drag.
 * A plain click (no movement) is left alone, so buttons inside the handle keep working.
 */
export function fileDragHandlers(id: string, start: (id: string) => void = (i) => getBridge().startFileDrag(i)) {
  return {
    onPointerDown(e: ReactPointerEvent) {
      if (e.button !== 0) return
      const x0 = e.clientX, y0 = e.clientY
      let fired = false
      const move = (ev: PointerEvent) => {
        if (fired || !(ev.buttons & 1)) return
        if (Math.hypot(ev.clientX - x0, ev.clientY - y0) < THRESHOLD_PX) return
        fired = true
        start(id)
        stop()
      }
      const stop = () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', stop); window.removeEventListener('pointercancel', stop) }
      window.addEventListener('pointermove', move); window.addEventListener('pointerup', stop); window.addEventListener('pointercancel', stop)
    },
  }
}
