import json

import httpx
import pytest
from conftest import SHEET, TOKEN
from fastapi.testclient import TestClient

from chordarium_core.ai.fallback import HELP, apply_rules
from chordarium_core.ai.loop import run_chat
from chordarium_core.ai.providers import (ChatResult, OpenAICompatibleProvider, ProviderError, RulesOnlyProvider, ToolCall)
from chordarium_core.app import create_app
from chordarium_core.remote import RemoteOut
from chordarium_core.session import Session
from chordarium_core.tools import ToolContext

GOOD_PLAN = {"style": "sinhala_ballad", "dynamics": "soft", "parts": [
    {"role": "piano", "pattern": "arpeggio_up", "density": 0.4, "velocity": [40, 60], "register": "mid"},
    {"role": "bass", "pattern": "root_fifth", "density": 0.5, "velocity": [55, 70], "register": "low"},
    {"role": "pad", "pattern": "sustain", "density": 0.2, "velocity": [35, 50], "register": "mid_high"},
    {"role": "drums", "pattern": "ballad_light", "density": 0.3, "velocity": [45, 75]}]}


class Scripted:
    name = "scripted"

    def __init__(self, results):
        self.results, self.calls = list(results), []

    async def chat(self, messages, tools):
        self.calls.append((messages, tools))
        return self.results.pop(0)

    async def health(self):
        return None


@pytest.fixture
def ctx(tmp_path):
    s = Session()
    s.load_sheet(SHEET)
    return ToolContext(s, RemoteOut(port=object()), tmp_path)


async def collect(gen):
    return [e async for e in gen]


@pytest.mark.asyncio
async def test_tool_loop_arranges_and_replies(ctx):
    p = Scripted([ChatResult(tool_calls=[ToolCall("1", "get_session", {})]),
                  ChatResult(tool_calls=[ToolCall("2", "arrange", {"plan": {**GOOD_PLAN, "section_id": "sec_chorus_1"}})]),
                  ChatResult(content="Arranged the chorus as a soft ballad.")])
    ev = await collect(run_chat(ctx, p, "arrange chorus 1 soft", [], "sec_chorus_1"))
    assert [e["type"] for e in ev] == ["chat.tool", "chat.tool", "chat.delta", "chat.done"]
    assert len(ctx.session.parts) == 4 and ev[1]["summary"] == "Arranged 4 parts"
    assert p.calls[0][0][0]["role"] == "system" and p.calls[0][1]  # tools offered


@pytest.mark.asyncio
async def test_invalid_plan_retried_once_then_defaults(ctx):
    bad = {**GOOD_PLAN, "section_id": "sec_chorus_1", "parts": [{"role": "bass", "pattern": "bogus"}]}
    p = Scripted([ChatResult(tool_calls=[ToolCall("1", "arrange", {"plan": bad})]),
                  ChatResult(tool_calls=[ToolCall("2", "arrange", {"plan": bad})]),
                  ChatResult(content="Done.")])
    ev = await collect(run_chat(ctx, p, "arrange", [], "sec_chorus_1"))
    tools = [e for e in ev if e["type"] == "chat.tool"]
    assert tools[0]["ok"] is False and tools[1]["ok"] is True and "style's defaults" in tools[1]["summary"]
    assert len(ctx.session.parts) == 4
    assert "style's defaults" in [e for e in ev if e["type"] == "chat.delta"][0]["text"]
    # the validation message was fed back to the model
    assert any("Fix these fields" in str(m.get("content")) for m in p.calls[1][0] if m["role"] == "tool")


@pytest.mark.asyncio
async def test_max_six_tool_calls(ctx):
    p = Scripted([ChatResult(tool_calls=[ToolCall(str(i), "get_session", {})]) for i in range(10)])
    ev = await collect(run_chat(ctx, p, "loop", []))
    assert sum(1 for e in ev if e["type"] == "chat.tool") == 6
    assert "too many steps" in ev[-2]["text"]


@pytest.mark.asyncio
async def test_json_mode_when_no_tool_support(ctx):
    p = Scripted([ChatResult(supports_tools=False),
                  ChatResult(content="Sure!\n```json\n" + json.dumps({**GOOD_PLAN, "section_id": "sec_chorus_1"}) + "\n```")])
    ev = await collect(run_chat(ctx, p, "arrange chorus", [], "sec_chorus_1"))
    assert len(ctx.session.parts) == 4 and ev[-1]["type"] == "chat.done"
    p2 = Scripted([ChatResult(supports_tools=False), ChatResult(content="no json here")])
    ev2 = await collect(run_chat(ctx, p2, "x", [], "sec_chorus_1"))
    assert "couldn't read a plan" in ev2[0]["text"]
    bad = {**GOOD_PLAN, "section_id": "sec_chorus_1", "parts": [{"role": "bass", "pattern": "bogus"}]}
    p3 = Scripted([ChatResult(supports_tools=False), ChatResult(content=json.dumps(bad))])
    ev3 = await collect(run_chat(ctx, p3, "x", [], "sec_chorus_1"))
    assert "defaults" in ev3[-2]["text"]


@pytest.mark.asyncio
async def test_provider_error_event(ctx):
    class Boom(Scripted):
        async def chat(self, m, t):
            raise ProviderError("Groq limit reached. Try again in a minute or switch provider.")
    ev = await collect(run_chat(ctx, Boom([]), "hi", []))
    assert ev[0]["type"] == "error" and "limit reached" in ev[0]["message"]


@pytest.mark.asyncio
async def test_rules_provider_via_loop(ctx):
    ctx.session.arrange(["sec_chorus_1"])
    ev = await collect(run_chat(ctx, RulesOnlyProvider(), "make the bass busier", [], "sec_chorus_1"))
    assert any(e["type"] == "chat.tool" and e["ok"] for e in ev) and ev[-1]["type"] == "chat.done"
    assert (await RulesOnlyProvider().health()).ok


def test_fallback_rules(ctx):
    s = ctx.session
    s.arrange(["sec_chorus_1"])
    pid = "part_sec_chorus_1_bass"
    d0, v0 = s.parts[pid].spec.density, s.parts[pid].spec.velocity
    reply, ev = apply_rules(s, "softer please", "sec_chorus_1")
    assert s.parts[pid].spec.velocity[1] < v0[1] and "Done" in reply and ev
    apply_rules(s, "louder", "sec_chorus_1")
    reply, _ = apply_rules(s, "busier bass", "sec_chorus_1")
    assert s.parts["part_sec_chorus_1_bass"].spec.density > s.parts["part_sec_chorus_1_piano"].spec.density - 1
    apply_rules(s, "simpler piano", "sec_chorus_1")
    apply_rules(s, "higher pad", "sec_chorus_1")
    assert s.parts["part_sec_chorus_1_pad"].spec.register == "high"
    apply_rules(s, "lower pad", "sec_chorus_1")
    apply_rules(s, "add fill", "sec_chorus_1")
    assert s.parts["part_sec_chorus_1_drums"].spec.fills == "end_of_section"
    assert apply_rules(s, "dance for me", "sec_chorus_1")[0] == HELP
    apply_rules(s, "no drums", "sec_chorus_1")
    assert "part_sec_chorus_1_drums" not in s.parts
    s.set_lock("sec_chorus_1", "bass", True)
    reply, ev = apply_rules(s, "louder bass", "sec_chorus_1")
    assert "locked" in reply and not any(e["ok"] for e in ev)
    assert "not found" in apply_rules(s, "louder", "zzz")[0]
    fresh = Session()
    assert "No song" in apply_rules(fresh, "louder")[0]


def test_fallback_arranges_when_empty(ctx):
    reply, ev = apply_rules(ctx.session, "arrange this", "sec_chorus_1")
    assert "Arranged" in reply and len(ctx.session.parts) == 4


def _provider(handler):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return OpenAICompatibleProvider("groq", "https://x.test/v1/", "KEY", "m", client=client)


@pytest.mark.asyncio
async def test_openai_provider_tool_calls_and_headers():
    seen = {}

    def handler(req):
        seen["auth"], seen["body"] = req.headers["authorization"], json.loads(req.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": None, "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "get_session", "arguments": "{}"}},
            {"function": {"name": "arrange", "arguments": "not json"}}]}}]})

    res = await _provider(handler).chat([{"role": "user", "content": "hi"}], [{"type": "function", "function": {}}])
    assert seen["auth"] == "Bearer KEY" and seen["body"]["tool_choice"] == "auto"
    assert res.tool_calls[0].name == "get_session" and res.tool_calls[1].arguments == {}


@pytest.mark.asyncio
async def test_openai_provider_errors_and_health():
    p = _provider(lambda r: httpx.Response(429, text="slow down"))
    with pytest.raises(ProviderError, match="limit reached"):
        await p.chat([], [])
    p = _provider(lambda r: httpx.Response(400, text="this model does not support tools"))
    assert (await p.chat([], [{"x": 1}])).supports_tools is False
    p = _provider(lambda r: httpx.Response(500, text="boom"))
    with pytest.raises(ProviderError, match="500"):
        await p.chat([], [])
    ok = _provider(lambda r: httpx.Response(200, json={"data": [{"id": "a"}, {"id": "b"}]}))
    h = await ok.health()
    assert h.ok and h.models == ["a", "b"]
    assert not (await _provider(lambda r: httpx.Response(401)).health()).ok
    assert not (await _provider(lambda r: httpx.Response(503)).health()).ok

    def down(req):
        raise httpx.ConnectError("refused")
    h = await _provider(down).health()
    assert not h.ok and "Can't reach" in h.detail


def test_chat_endpoint_streams_ndjson(tmp_path):
    prov = Scripted([ChatResult(tool_calls=[ToolCall("1", "arrange", {"plan": {**GOOD_PLAN, "section_id": "sec_chorus_1"}})]),
                     ChatResult(content="Done.")])
    app = create_app(home=tmp_path, remote=RemoteOut(port=object()), token=TOKEN, provider_factory=lambda c: prov)
    c = TestClient(app, headers={"X-Chordarium-Token": TOKEN})
    c.post("/song/parse", json={"text": SHEET})
    r = c.post("/chat", json={"message": "arrange chorus 1", "section_id": "sec_chorus_1"})
    lines = [json.loads(x) for x in r.text.splitlines()]
    assert [l["type"] for l in lines] == ["chat.tool", "chat.delta", "chat.done"]
    assert c.post("/chat", json={"message": " "}).status_code == 422


def test_chat_rules_default(loaded):
    loaded.c.post("/arrange", json={"section_ids": ["sec_chorus_1"]})
    r = loaded.c.post("/chat", json={"message": "softer", "section_id": "sec_chorus_1"})
    assert '"chat.tool"' in r.text and '"chat.done"' in r.text
