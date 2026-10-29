"""FastAPI app: REST + WebSocket hub on 127.0.0.1 (spec 9). Every call except /health needs the local token."""
from __future__ import annotations

import asyncio
import hmac
import json
from pathlib import Path
from typing import Callable

from chordarium_engine.arrange import PlanError
from chordarium_engine.styles import load_styles
from fastapi import Depends, FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from . import __version__
from .ai.loop import run_chat
from .ai.providers import OpenAICompatibleProvider, Provider, ProviderError, RulesOnlyProvider
from .config import Config, data_dir, get_api_key, get_token, load_config, save_config, set_api_key
from .remote import RemoteOut
from .session import Session, SessionError
from .tools import TOOLS, ToolContext, ToolError, call_tool, openai_schema

ProviderFactory = Callable[[Config], Provider]


def _activity(name: str, args: dict, out) -> str | None:
    """One-line summary of a tool call made by an MCP client (feeds the Assistant activity list)."""
    if name == "arrange" and isinstance(out, dict):
        secs = sorted({p["section_id"] for p in out.get("parts", [])})
        return f"Claude arranged {', '.join(secs) or 'the song'} — {len(out.get('parts', []))} parts"
    if name in ("edit_part", "regenerate_part") and isinstance(out, dict):
        return f"{'Regenerated' if name == 'regenerate_part' else 'Edited'} {out.get('role')} · {out.get('section_id')}"
    if name == "set_part_lock" and isinstance(out, dict):
        return f"{'Locked' if out.get('locked') else 'Unlocked'} {out.get('role')} · {out.get('section_id')}"
    if name == "load_chord_sheet" and isinstance(out, dict):
        return f"Loaded “{out.get('title')}”"
    if name == "export_midi" and isinstance(out, dict):
        return f"Exported {len(out.get('files', []))} MIDI file(s)"
    if name == "transport":
        return f"Cubase: {args.get('action')}"
    return None


def default_provider_factory(cfg: Config) -> Provider:
    if cfg.provider in ("rules", "mcp", ""):
        return RulesOnlyProvider()
    return OpenAICompatibleProvider(cfg.provider, cfg.resolved_base_url(), get_api_key(cfg.provider), cfg.model)


class Hub:
    def __init__(self) -> None:
        self.queues: dict[asyncio.Queue, asyncio.AbstractEventLoop] = {}

    def broadcast(self, event: dict) -> None:
        for q, loop in list(self.queues.items()):
            try:
                loop.call_soon_threadsafe(q.put_nowait, event)
            except RuntimeError:  # that connection's loop is gone
                self.queues.pop(q, None)


def create_app(home: Path | None = None, session: Session | None = None, remote: RemoteOut | None = None,
               provider_factory: ProviderFactory = default_provider_factory, token: str | None = None) -> FastAPI:
    home = home or data_dir()
    cfg = load_config(home)
    tok = token or get_token(home)
    sess = session or Session()
    rem = remote or RemoteOut(cfg.cubase_port_name)
    ctx = ToolContext(sess, rem, home / "exports")
    hub = Hub()
    history: list[dict] = []
    state = {"cfg": cfg, "save_handle": None}
    app = FastAPI(title="Chordarium Studio core", version=__version__)
    app.state.session, app.state.hub, app.state.ctx = sess, hub, ctx
    # Browser dev mode (localhost:5173) and the plugin WebView resource origin; still token-protected.
    app.add_middleware(CORSMiddleware, allow_origin_regex=r"^(https?://(localhost|127\.0\.0\.1)(:\d+)?|https://juce\.backend|juce://juce\.backend)$",
                       allow_methods=["*"], allow_headers=["*"])

    def schedule_save() -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            sess.save(home)
            return
        if state["save_handle"]:
            state["save_handle"].cancel()
        state["save_handle"] = loop.call_later(0.5, lambda: sess.save(home))

    def on_event(event: str, payload: dict) -> None:
        if event == "session.updated":
            hub.broadcast({"type": event, "session": sess.summary()})
        elif event == "part.updated":
            part = sess.parts.get(payload.get("part_id", ""))
            hub.broadcast({"type": event, "part": part.model_dump(mode="json") if part else None})
        else:
            hub.broadcast({"type": event, **payload})
        schedule_save()

    sess.listeners.append(on_event)

    def auth(x_chordarium_token: str | None = Header(default=None)) -> None:
        if not x_chordarium_token or not hmac.compare_digest(x_chordarium_token, tok):
            raise HTTPException(401, "Missing or wrong X-Chordarium-Token")

    @app.exception_handler(SessionError)
    @app.exception_handler(ToolError)
    @app.exception_handler(ProviderError)
    async def _bad(request: Request, exc: Exception):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(PlanError)
    async def _bad_plan(request: Request, exc: PlanError):
        return JSONResponse({"detail": str(exc), "errors": exc.errors}, status_code=422)

    # ---- health / config ----
    @app.get("/health")
    async def health():
        return {"status": "ok", "version": __version__, "provider": state["cfg"].provider,
                "cubase_remote": rem.available()}

    @app.get("/config", dependencies=[Depends(auth)])
    async def get_config():
        c = state["cfg"]
        return {**c.model_dump(), "has_key": bool(get_api_key(c.provider)) if c.provider not in ("rules", "mcp") else False}

    @app.put("/config", dependencies=[Depends(auth)])
    async def put_config(body: dict):
        key = body.pop("api_key", None)
        new = Config.model_validate({**state["cfg"].model_dump(), **body})
        if key:
            if not set_api_key(new.provider, key):
                raise HTTPException(500, "Could not store the API key in the system keyring.")
        state["cfg"] = new
        save_config(new, home)
        hub.broadcast({"type": "provider.status", "provider": new.provider})
        return {**new.model_dump(), "has_key": bool(key) or bool(get_api_key(new.provider))}

    @app.post("/provider/test", dependencies=[Depends(auth)])
    async def provider_test():
        h = await provider_factory(state["cfg"]).health()
        hub.broadcast({"type": "provider.status", "provider": state["cfg"].provider, "ok": h.ok})
        return {"ok": h.ok, "detail": h.detail, "models": h.models}

    # ---- session / song ----
    @app.get("/session", dependencies=[Depends(auth)])
    async def get_session():
        return sess.summary()

    @app.get("/session/snapshot", dependencies=[Depends(auth)])
    async def snapshot():
        return sess.snapshot()

    @app.put("/session/snapshot", dependencies=[Depends(auth)])
    async def restore(body: dict):
        sess.restore(body)
        sess.emit("session.updated")
        return sess.summary()

    @app.post("/session/new", dependencies=[Depends(auth)])
    async def new_session():
        sess.new_song()
        return sess.summary()

    @app.post("/song/parse", dependencies=[Depends(auth)])
    async def parse(body: dict):
        if not (body.get("text") or "").strip():
            raise HTTPException(422, "text is required")
        return sess.load_sheet(body["text"], body.get("title")).model_dump(mode="json")

    @app.post("/song/preview", dependencies=[Depends(auth)])
    async def preview(body: dict):
        from chordarium_engine.parser.sheet import parse_sheet
        return parse_sheet(body.get("text") or "", body.get("title")).model_dump(mode="json")

    @app.patch("/song", dependencies=[Depends(auth)])
    async def patch_song(body: dict):
        return sess.patch_song(body).model_dump(mode="json")

    @app.post("/chords/validate", dependencies=[Depends(auth)])
    async def validate_chords(body: dict):
        from chordarium_engine.parser.chords import ChordParseError, is_no_chord, parse_chord
        out = []
        for sym in body.get("symbols", []):
            if is_no_chord(str(sym)):
                out.append({"symbol": sym, "ok": True, "canonical": "N.C."})
                continue
            try:
                out.append({"symbol": sym, "ok": True, "canonical": parse_chord(str(sym)).symbol})
            except ChordParseError as e:
                out.append({"symbol": sym, "ok": False, "error": str(e)})
        return {"results": out}

    @app.post("/select", dependencies=[Depends(auth)])
    async def select(body: dict):
        sess.selected_section_id = sess.find_section(body.get("section_id")).id
        return {"selected_section_id": sess.selected_section_id}

    @app.post("/undo", dependencies=[Depends(auth)])
    async def undo():
        return {"ok": sess.undo()}

    @app.post("/redo", dependencies=[Depends(auth)])
    async def redo():
        return {"ok": sess.redo()}

    # ---- styles / arrangement ----
    @app.get("/styles", dependencies=[Depends(auth)])
    async def styles():
        return call_tool(ctx, "list_styles", {})

    @app.post("/arrange", dependencies=[Depends(auth)])
    async def arrange(body: dict):
        return call_tool(ctx, "arrange", body)

    @app.get("/parts/{part_id}", dependencies=[Depends(auth)])
    async def get_part(part_id: str):
        p = sess.parts.get(part_id)
        if p is None:
            raise HTTPException(404, "Part not found")
        return p.model_dump(mode="json")

    def _part(part_id: str):
        p = sess.parts.get(part_id)
        if p is None:
            raise HTTPException(404, "Part not found")
        return p

    @app.post("/parts/{part_id}/edit", dependencies=[Depends(auth)])
    async def edit_part(part_id: str, body: dict):
        p = _part(part_id)
        return sess.edit_part(p.section_id, p.role, body).model_dump(mode="json")

    @app.put("/parts/{part_id}/notes", dependencies=[Depends(auth)])
    async def put_notes(part_id: str, body: dict):
        _part(part_id)
        return sess.set_notes(part_id, body.get("notes") or []).model_dump(mode="json")

    @app.post("/parts/{part_id}/regenerate", dependencies=[Depends(auth)])
    async def regen(part_id: str, body: dict | None = None):
        p = _part(part_id)
        return sess.regenerate_part(p.section_id, p.role, (body or {}).get("seed")).model_dump(mode="json")

    @app.post("/parts/{part_id}/lock", dependencies=[Depends(auth)])
    async def lock(part_id: str, body: dict):
        p = _part(part_id)
        return Session.part_summary(sess.set_lock(p.section_id, p.role, bool(body.get("locked", True))))

    @app.delete("/parts/{part_id}", dependencies=[Depends(auth)])
    async def clear(part_id: str):
        p = _part(part_id)
        sess.clear_part(p.section_id, p.role)
        return {"ok": True}

    @app.post("/export", dependencies=[Depends(auth)])
    async def export(body: dict):
        return call_tool(ctx, "export_midi", body)

    @app.post("/remote/{action}", dependencies=[Depends(auth)])
    async def remote(action: str):
        try:
            call_tool(ctx, "transport", {"action": action})
        except ToolError as e:
            raise HTTPException(409, str(e)) from e
        return {"ok": True}

    # ---- tools (single source of truth, used by the MCP adapter) ----
    @app.get("/tools", dependencies=[Depends(auth)])
    async def tools():
        return {"tools": [{"name": t.name, "description": t.description, "parameters": t.parameters} for t in TOOLS.values()],
                "openai": openai_schema()}

    @app.post("/tools/{name}", dependencies=[Depends(auth)])
    async def tool(name: str, body: dict | None = None):
        if name not in TOOLS:
            raise HTTPException(404, f"Unknown tool {name}")
        out = call_tool(ctx, name, body)
        note = _activity(name, body or {}, out)
        if note:
            hub.broadcast({"type": "activity", "tool": name, "summary": note, "ok": True})
        return out

    # ---- chat ----
    @app.post("/chat", dependencies=[Depends(auth)])
    async def chat(body: dict):
        message = (body.get("message") or "").strip()
        if not message:
            raise HTTPException(422, "message is required")
        provider = provider_factory(state["cfg"])

        async def stream():
            async for ev in run_chat(ctx, provider, message, history, body.get("section_id")):
                hub.broadcast(ev)
                yield json.dumps(ev) + "\n"

        return StreamingResponse(stream(), media_type="application/x-ndjson")

    # ---- websocket ----
    @app.websocket("/ws")
    async def ws(sock: WebSocket):
        await sock.accept()
        try:
            hello = await asyncio.wait_for(sock.receive_json(), 5)
        except Exception:
            await sock.close(4400)
            return
        if hello.get("type") != "hello" or not hmac.compare_digest(str(hello.get("token", "")), tok):
            await sock.close(4401)
            return
        q: asyncio.Queue = asyncio.Queue()
        hub.queues[q] = asyncio.get_running_loop()
        await sock.send_json({"type": "hello.ok", "version": __version__, "client": hello.get("client")})

        async def pump():
            while True:
                await sock.send_json(await q.get())

        task = asyncio.create_task(pump())
        try:
            while True:
                msg = await sock.receive_json()
                if msg.get("type") == "preview.request":
                    parts = [p.model_dump(mode="json") for p in sess.parts.values()
                             if p.section_id == msg.get("section_id")]
                    q.put_nowait({"type": "preview.parts", "section_id": msg.get("section_id"), "parts": parts})
        except WebSocketDisconnect:
            pass
        finally:
            task.cancel()
            hub.queues.pop(q, None)

    return app


def main() -> None:
    import argparse
    import uvicorn
    ap = argparse.ArgumentParser(prog="chordarium-core")
    ap.add_argument("--port", type=int)
    args = ap.parse_args()
    cfg = load_config()
    uvicorn.run(create_app(), host="127.0.0.1", port=args.port or cfg.port, log_level="warning")


if __name__ == "__main__":
    main()
