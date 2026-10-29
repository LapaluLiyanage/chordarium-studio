import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

afterEach(() => cleanup())
// GSAP/ResizeObserver/matchMedia/canvas are not in jsdom; reduced motion keeps animations inert in tests.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (q: string) => ({ matches: q.includes('reduce'), media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, onchange: null, dispatchEvent: () => false }),
})
globalThis.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} } as unknown as typeof ResizeObserver
HTMLCanvasElement.prototype.getContext = vi.fn(() => ({ clearRect() {}, fillRect() {}, strokeRect() {}, beginPath() {}, roundRect() {}, fill() {}, scale() {}, setTransform() {}, set fillStyle(_v: string) {}, set globalAlpha(_v: number) {}, set strokeStyle(_v: string) {}, set lineWidth(_v: number) {} })) as never
