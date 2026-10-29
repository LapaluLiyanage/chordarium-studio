import type { AppConfig, ArrangementPlan, ChatEvent, Part, Snapshot, Song, StyleInfo } from '../types'

export interface CoreConn { baseUrl: string; token: string }
export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message) }
}

/** All core calls go through here. Components never call fetch directly. */
export class CoreApi {
  private f: typeof fetch
  constructor(public conn: CoreConn, fetchImpl?: typeof fetch) { this.f = fetchImpl ?? ((...a) => fetch(...a)) }

  private async req<T>(method: string, path: string, body?: unknown): Promise<T> {
    let r: Response
    try {
      r = await this.f(this.conn.baseUrl + path, {
        method, headers: { 'Content-Type': 'application/json', 'X-Chordarium-Token': this.conn.token },
        body: body === undefined ? undefined : JSON.stringify(body),
      })
    } catch {
      throw new ApiError(0, "Can't reach the engine. Restart the plugin or check logs.")
    }
    if (!r.ok) {
      let detail = r.statusText
      try { detail = (await r.json()).detail ?? detail } catch { /* keep statusText */ }
      throw new ApiError(r.status, typeof detail === 'string' ? detail : JSON.stringify(detail))
    }
    return r.json() as Promise<T>
  }

  health = () => this.req<{ status: string; version: string; provider: string; cubase_remote: boolean }>('GET', '/health')
  snapshot = () => this.req<Snapshot>('GET', '/session/snapshot')
  parse = (text: string, title?: string) => this.req<Song>('POST', '/song/parse', { text, title })
  preview = (text: string) => this.req<Song>('POST', '/song/preview', { text })
  newSession = () => this.req<unknown>('POST', '/session/new', {})
  patchSong = (patch: Partial<Song>) => this.req<Song>('PATCH', '/song', patch)
  select = (section_id: string) => this.req('POST', '/select', { section_id })
  undo = () => this.req<{ ok: boolean }>('POST', '/undo')
  redo = () => this.req<{ ok: boolean }>('POST', '/redo')
  styles = () => this.req<{ styles: StyleInfo[] }>('GET', '/styles')
  arrange = (b: { section_ids?: string[]; plan?: Partial<ArrangementPlan>; style?: string; dynamics?: string }) => this.req('POST', '/arrange', b)
  editPart = (id: string, changes: Record<string, unknown>) => this.req<Part>('POST', `/parts/${id}/edit`, changes)
  regenerate = (id: string, seed?: number) => this.req<Part>('POST', `/parts/${id}/regenerate`, { seed })
  lock = (id: string, locked: boolean) => this.req('POST', `/parts/${id}/lock`, { locked })
  clearPart = (id: string) => this.req('DELETE', `/parts/${id}`)
  exportMidi = (scope: 'part' | 'section' | 'song', ids?: string[]) => this.req<{ files: string[]; message: string }>('POST', '/export', { scope, ids })
  remote = (action: string) => this.req('POST', `/remote/${action}`)
  getConfig = () => this.req<AppConfig>('GET', '/config')
  putConfig = (b: Partial<AppConfig> & { api_key?: string }) => this.req<AppConfig>('PUT', '/config', b)
  testProvider = () => this.req<{ ok: boolean; detail: string; models: string[] }>('POST', '/provider/test')
  validateChords = (symbols: string[]) =>
    this.req<{ results: { symbol: string; ok: boolean; canonical?: string; error?: string }[] }>('POST', '/chords/validate', { symbols })

  /** Streams NDJSON chat events. */
  async chat(message: string, sectionId: string | null, onEvent: (e: ChatEvent) => void): Promise<void> {
    let r: Response
    try {
      r = await this.f(this.conn.baseUrl + '/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Chordarium-Token': this.conn.token },
        body: JSON.stringify({ message, section_id: sectionId }),
      })
    } catch { throw new ApiError(0, "Can't reach the engine. Restart the plugin or check logs.") }
    if (!r.ok || !r.body) throw new ApiError(r.status, 'Chat failed')
    const reader = r.body.getReader(); const dec = new TextDecoder(); let buf = ''
    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      buf += dec.decode(value, { stream: true })
      const lines = buf.split('\n'); buf = lines.pop() ?? ''
      for (const l of lines) if (l.trim()) onEvent(JSON.parse(l) as ChatEvent)
    }
  }

  /** WebSocket with automatic reconnect every 3 s. Returns a close function. */
  connectWs(onEvent: (e: Record<string, unknown>) => void, onState: (up: boolean) => void, WS: typeof WebSocket = WebSocket): () => void {
    let ws: WebSocket | null = null; let stopped = false; let timer: ReturnType<typeof setTimeout> | undefined
    const open = () => {
      ws = new WS(this.conn.baseUrl.replace(/^http/, 'ws') + '/ws')
      ws.onopen = () => ws?.send(JSON.stringify({ type: 'hello', client: 'ui', token: this.conn.token }))
      ws.onmessage = (m) => {
        const e = JSON.parse(String(m.data)); if (e.type === 'hello.ok') onState(true)
        onEvent(e)
      }
      ws.onclose = () => { onState(false); if (!stopped) timer = setTimeout(open, 3000) }
    }
    open()
    return () => { stopped = true; clearTimeout(timer); ws?.close() }
  }
}
