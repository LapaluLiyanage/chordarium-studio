"""Thin, stateless MCP adapter (spec 10). Tool names/descriptions come from chordarium_core.tools; calls go to core over HTTP."""
from __future__ import annotations

import httpx
from chordarium_core.ai.prompts import SYSTEM_PROMPT
from chordarium_core.config import get_token, load_config
from chordarium_core.tools import TOOLS
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

NOT_RUNNING = "Open Chordarium Studio in your DAW first."


class CoreClient:
    def __init__(self, client: httpx.Client | None = None):
        self._client = client

    def _c(self) -> httpx.Client:
        if self._client is None:
            cfg = load_config()
            self._client = httpx.Client(base_url=f"http://127.0.0.1:{cfg.port}", headers={"X-Chordarium-Token": get_token()}, timeout=60)
        return self._client

    def call(self, name: str, args: dict) -> dict:
        args = {k: v for k, v in args.items() if v is not None}
        try:
            r = self._c().post(f"/tools/{name}", json=args)
        except httpx.TransportError as e:
            raise ToolError(NOT_RUNNING) from e
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except ValueError:
                detail = r.text
            raise ToolError(str(detail))
        return r.json()


def build_server(core: CoreClient | None = None) -> MCPServer:
    core = core or CoreClient()
    server = MCPServer("chordarium-studio", instructions=SYSTEM_PROMPT)
    d = lambda n: TOOLS[n].description  # noqa: E731 - single source of truth for descriptions

    @server.tool(name="get_session", description=d("get_session"))
    def get_session() -> dict:
        return core.call("get_session", {})

    @server.tool(name="load_chord_sheet", description=d("load_chord_sheet"))
    def load_chord_sheet(text: str, title: str | None = None) -> dict:
        return core.call("load_chord_sheet", {"text": text, "title": title})

    @server.tool(name="list_styles", description=d("list_styles"))
    def list_styles() -> dict:
        return core.call("list_styles", {})

    @server.tool(name="arrange", description=d("arrange"))
    def arrange(section_ids: list[str] | None = None, plan: dict | None = None,
                style: str | None = None, dynamics: str | None = None) -> dict:
        return core.call("arrange", {"section_ids": section_ids, "plan": plan, "style": style, "dynamics": dynamics})

    @server.tool(name="edit_part", description=d("edit_part"))
    def edit_part(role: str, changes: dict, section_id: str | None = None) -> dict:
        return core.call("edit_part", {"section_id": section_id, "role": role, "changes": changes})

    @server.tool(name="regenerate_part", description=d("regenerate_part"))
    def regenerate_part(role: str, section_id: str | None = None, seed: int | None = None) -> dict:
        return core.call("regenerate_part", {"section_id": section_id, "role": role, "seed": seed})

    @server.tool(name="set_part_lock", description=d("set_part_lock"))
    def set_part_lock(role: str, locked: bool, section_id: str | None = None) -> dict:
        return core.call("set_part_lock", {"section_id": section_id, "role": role, "locked": locked})

    @server.tool(name="export_midi", description=d("export_midi"))
    def export_midi(scope: str = "section", ids: list[str] | None = None) -> dict:
        return core.call("export_midi", {"scope": scope, "ids": ids})

    @server.tool(name="transport", description=d("transport"))
    def transport(action: str) -> dict:
        return core.call("transport", {"action": action})

    return server


def main() -> None:
    build_server().run("stdio")


if __name__ == "__main__":
    main()
