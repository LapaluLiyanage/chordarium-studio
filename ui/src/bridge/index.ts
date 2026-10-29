import type { CoreConn } from '../api/core'
import type { Role } from '../types'
import { createJuceBridge } from './juce'
import { createMockBridge } from './mock'

export interface Position { playing: boolean; quarters: number; bpm: number }
export interface DragRect { partId: string; x: number; y: number; w: number; h: number }
export interface HostInfo { host: string; sampleRate: number; bpm: number; webview2?: boolean }
export type SyncMode = 'host' | 'free'
export interface RoleMix { mute: boolean; solo: boolean; gain: number }

/** All plugin calls go through here. Plugin mode = JUCE native bridge, browser dev mode = mock. */
export interface Bridge {
  kind: 'mock' | 'juce'
  getCoreConnection(): Promise<CoreConn>
  previewPlay(sectionId: string, lengthQuarters: number, bpm: number): void
  previewStop(): void
  setLoop(on: boolean): void
  setRoleMix(role: Role, mix: RoleMix): void
  setSyncMode(mode: SyncMode): void
  reportDragRects(rects: DragRect[]): void
  revealFile(path: string): void
  /** Start an OS file drag for a part ("section:<id>" for the whole section). Call while the mouse button is held. */
  startFileDrag(id: string): void
  getHostInfo(): Promise<HostInfo>
  position(): Position
  onMeter(cb: (levels: Record<Role, number>) => void): () => void
  onDragDone(cb: (partId: string) => void): () => void
}

let current: Bridge | null = null
export function getBridge(): Bridge {
  if (!current) current = typeof window !== 'undefined' && (window as unknown as { __JUCE__?: unknown }).__JUCE__ ? createJuceBridge() : createMockBridge()
  return current
}
export function setBridge(b: Bridge | null) { current = b }
