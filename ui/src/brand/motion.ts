// Chordarium motion presets — extracted from client/src/motion.ts, Effects.tsx, Hero.tsx.
// GSAP 3 is the animation engine (same as Chordarium). Only animate transform/opacity.
import { gsap } from 'gsap'

export const motionOK = () =>
  typeof window !== 'undefined' && typeof window.matchMedia === 'function' &&
  !window.matchMedia('(prefers-reduced-motion: reduce)').matches

export const ease = {
  chordFlip: 'back.out(2)', enter: 'power3.out', wordmark: 'power4.out',
  logoPop: 'back.out(1.6)', elastic: 'elastic.out(1,.35)', cursor: 'power3', loop: 'sine.inOut',
}

/** Signature: the active chord "flips up" into place on every chord change (0.5s). */
export function flipIn(el: Element | null) {
  if (!el || !motionOK()) return
  gsap.fromTo(el, { yPercent: 35, opacity: 0, rotateX: -70, transformPerspective: 600 },
    { yPercent: 0, opacity: 1, rotateX: 0, duration: 0.5, ease: ease.chordFlip, overwrite: true })
}
/** Splash: logo spins in (scale 0, -180deg → 1, 0) ~1s. Wordmark letters rise with 0.055s stagger. */
export const splashLogo = (el: Element) =>
  gsap.from(el, { scale: 0, rotation: -180, duration: 1, delay: 0.4, ease: ease.logoPop })
export const wordmarkIn = (sel: string) =>
  gsap.from(sel, { yPercent: 115, duration: 1, ease: ease.wordmark, stagger: 0.055 })
/** Panel / card entrance: rise 30–60px + fade. */
export const riseIn = (el: Element, y = 30) =>
  gsap.from(el, { y, opacity: 0, duration: 0.8, ease: ease.enter })
/** Letter hover bounce: lift -22px, then elastic settle. */
export const letterBounce = (el: Element) =>
  gsap.timeline().to(el, { y: -22, duration: 0.22, ease: 'power2.out' }).to(el, { y: 0, duration: 0.8, ease: ease.elastic })
/** Primary-CTA pulse ring (idle attention; stop when not visible). */
export const pulseRing = (el: Element) =>
  gsap.fromTo(el, { boxShadow: '0 0 0 0 rgba(242,145,61,.5)' }, { boxShadow: '0 0 0 18px rgba(242,145,61,0)', duration: 1.6, repeat: -1, ease: 'power2.out' })
/** Bobbing hint arrow. */
export const bob = (el: Element) => gsap.to(el, { y: 5, duration: 0.6, repeat: -1, yoyo: true, ease: ease.loop })
/** Magnetic hover (buttons): follow pointer 30% x / 40% y; release with elastic.out(1,.4) 0.7s. */
/** Floating notes burst on play/click: 0.9–1.4s, power2.out, random drift ±30px, rise 40–80px, fade. */
/** Chord lane: playhead fixed at 50%, track translateX scrolls under it (will-change: transform). */
/** Structure/section blocks fill with section colour when active; looping adds 3px cream ring. */
