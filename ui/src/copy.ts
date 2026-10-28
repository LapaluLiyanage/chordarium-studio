// User-facing copy for every state in UI spec section 6. Short, musician language.
export const COPY = {
  starting: 'Starting Chordarium engine…',
  unreachable: "Can't reach the engine. Restart the plugin or check logs.",
  noSong: 'Paste a chord sheet to begin.',
  barsNeedCheck: (n: number) => `${n} bar${n === 1 ? '' : 's'} need${n === 1 ? 's' : ''} a quick check`,
  noAi: 'No AI connected — quick edits still work. Connect one in Settings.',
  planning: (section: string) => `Planning ${section}…`,
  usedDefault: (what: string) => `Used the style default for the ${what}.`,
  providerLimit: (name: string) => `${name} limit reached. Try again in a minute or switch provider.`,
  cubaseMissing: 'Optional: set up Cubase link for transport control.',
  locked: (role: string) => `${role} is locked. Unlock to change it.`,
  webview2: 'Chordarium Studio needs Microsoft Edge WebView2.',
  quickHelp: 'Without an AI connected I can do: softer, louder, busier, simpler, add fill, remove a part.',
} as const
