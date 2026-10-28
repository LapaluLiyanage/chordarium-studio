import httpx
import pytest
from chordarium_core.app import create_app
from chordarium_core.remote import RemoteOut
from chordarium_core.tools import TOOLS
from fastapi.testclient import TestClient
from mcp import Client

from chordarium_mcp.server import NOT_RUNNING, CoreClient, build_server

TOKEN = "m" * 64
SHEET = "Key: G\n[Chorus 1]\n| G | Em C | D | G |"


@pytest.fixture
def core(tmp_path):
    app = create_app(home=tmp_path, remote=RemoteOut(port=type("P", (), {"send_message": lambda self, m: None})()), token=TOKEN)
    return TestClient(app, headers={"X-Chordarium-Token": TOKEN})


async def test_tools_match_core_registry_and_flow(core):
    server = build_server(CoreClient(core))
    async with Client(server) as c:
        listed = await c.list_tools()
        assert {t.name for t in listed.tools} == set(TOOLS)  # single source of truth
        r = await c.call_tool("load_chord_sheet", {"text": SHEET})
        assert not r.is_error
        r = await c.call_tool("arrange", {"section_ids": ["sec_chorus_1"], "style": "sinhala_ballad", "dynamics": "soft"})
        assert not r.is_error
        r = await c.call_tool("get_session", {})
        assert "piano" in str(r.content)
        r = await c.call_tool("edit_part", {"role": "bass", "changes": {"density": 0.9}})
        assert not r.is_error
        r = await c.call_tool("regenerate_part", {"role": "bass", "seed": 3})
        r = await c.call_tool("set_part_lock", {"role": "bass", "locked": True})
        r = await c.call_tool("edit_part", {"role": "bass", "changes": {"density": 0.1}})
        assert r.is_error and "locked" in str(r.content)
        r = await c.call_tool("export_midi", {"scope": "section"})
        assert ".mid" in str(r.content)
        r = await c.call_tool("list_styles", {})
        assert "sinhala_ballad" in str(r.content)
        r = await c.call_tool("transport", {"action": "play"})
        assert not r.is_error


async def test_core_not_running_message():
    def refuse(request):
        raise httpx.ConnectError("refused")
    client = httpx.Client(transport=httpx.MockTransport(refuse), base_url="http://127.0.0.1:1")
    async with Client(build_server(CoreClient(client))) as c:
        r = await c.call_tool("get_session", {})
        assert r.is_error and NOT_RUNNING in str(r.content)


def test_instructions_are_system_prompt():
    assert "arranging assistant" in build_server(CoreClient(None)).instructions
