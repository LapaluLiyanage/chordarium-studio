import type { Role, SectionKind } from './types'
export const SECTION_COLOR: Record<SectionKind, string> = {
  intro: 'var(--sec-intro)', verse: 'var(--sec-verse)', pre_chorus: 'var(--sec-verse)', chorus: 'var(--sec-chorus)',
  bridge: 'var(--sec-bridge)', interlude: 'var(--sec-interlude)', solo: 'var(--sec-interlude)', outro: 'var(--sec-outro)', other: 'var(--sec-other)',
}
export const ROLE_COLOR: Record<Role, string> = {
  piano: 'var(--role-piano)', bass: 'var(--role-bass)', pad: 'var(--role-pad)', drums: 'var(--role-drums)',
}
export const ROLE_LABEL: Record<Role, string> = { piano: 'Piano', bass: 'Bass', pad: 'Pad', drums: 'Drums' }
export const REGISTER_LABEL = { low: 'Low', mid_low: 'Mid-lo', mid: 'Mid', mid_high: 'Mid-hi', high: 'High' } as const
export const PATTERN_LABEL = (p: string) => p.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())
