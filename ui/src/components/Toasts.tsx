import { useEffect } from 'react'
import { useStore } from '../store'

export function Toasts() {
  const { toasts, dismissToast } = useStore()
  useEffect(() => {
    const t = toasts.map((x) => setTimeout(() => dismissToast(x.id), 6000))
    return () => t.forEach(clearTimeout)
  }, [toasts, dismissToast])
  return <div className="toasts" role="status" aria-live="polite">{toasts.map((t) => <div key={t.id} className={`toast ${t.kind}`}>{t.text}<button className="icon-btn" aria-label="Dismiss" onClick={() => dismissToast(t.id)}>×</button></div>)}</div>
}
