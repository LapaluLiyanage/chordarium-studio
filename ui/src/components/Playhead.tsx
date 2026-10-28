import { useEffect, useRef } from 'react'
import { getBridge } from '../bridge'

export function Playhead({ quarters }: { quarters: number }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    let raf = 0
    const tick = () => {
      const p = getBridge().position()
      if (ref.current) {
        ref.current.style.display = p.playing ? 'block' : 'none'
        ref.current.style.left = `${((p.quarters % quarters) / quarters) * 100}%`
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [quarters])
  return <div ref={ref} className="playhead" style={{ display: 'none' }} aria-hidden />
}
