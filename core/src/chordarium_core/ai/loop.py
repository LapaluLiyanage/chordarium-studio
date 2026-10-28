"""In-plugin chat loop (spec 8.4): tool calling, one validation retry, defaults fallback, JSON mode."""
from __future__ import annotations

import json
import re
from typing import AsyncIterator

from ..tools import ToolContext, ToolError, call_tool, openai_schema
from .fallback import apply_rules
from .prompts import JSON_MODE_PROMPT, SYSTEM_PROMPT
from .providers import Provider, ProviderError

MAX_TOOL_CALLS = 6


def _extract_json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except ValueError:
        return None


async def run_chat(ctx: ToolContext, provider: Provider, message: str, history: list[dict],
                   section_id: str | None = None) -> AsyncIterator[dict]:
    """Yields events: chat.delta {text}, chat.tool {name, ok, summary}, error {message}, chat.done."""
    if provider.name == "rules":
        reply, events = apply_rules(ctx.session, message, section_id)
        for e in events:
            yield {"type": "chat.tool", **e}
        yield {"type": "chat.delta", "text": reply}
        yield {"type": "chat.done"}
        return

    msgs = [{"role": "system", "content": SYSTEM_PROMPT}, *history, {"role": "user", "content": message}]
    if section_id:
        msgs.insert(1, {"role": "system", "content": f"The selected section is {section_id}."})
    tools = openai_schema()
    retried: set[str] = set()
    calls_made = 0
    notes: list[str] = []
    try:
        while True:
            res = await provider.chat(msgs, tools)
            if not res.supports_tools:
                async for ev in _json_mode(ctx, provider, message, section_id):
                    yield ev
                yield {"type": "chat.done"}
                return
            if not res.tool_calls:
                text = res.content.strip()
                if notes:
                    text = (text + " " + " ".join(notes)).strip()
                if text:
                    yield {"type": "chat.delta", "text": text}
                    history.append({"role": "user", "content": message})
                    history.append({"role": "assistant", "content": res.content})
                    del history[:-20]
                yield {"type": "chat.done"}
                return
            msgs.append({"role": "assistant", "content": res.content or None, "tool_calls": [
                {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": json.dumps(c.arguments)}}
                for c in res.tool_calls]})
            for c in res.tool_calls:
                calls_made += 1
                if calls_made > MAX_TOOL_CALLS:
                    yield {"type": "chat.delta", "text": "I stopped after too many steps. Tell me what to adjust next."}
                    yield {"type": "chat.done"}
                    return
                try:
                    out = call_tool(ctx, c.name, c.arguments)
                    yield {"type": "chat.tool", "name": c.name, "ok": True, "summary": _summ(c.name, out)}
                    msgs.append({"role": "tool", "tool_call_id": c.id, "content": json.dumps(out)[:6000]})
                except ToolError as e:
                    if c.name == "arrange" and c.name in retried:
                        note = await _apply_defaults(ctx, c.arguments, section_id)
                        notes.append(note)
                        yield {"type": "chat.tool", "name": "arrange", "ok": True, "summary": note}
                        msgs.append({"role": "tool", "tool_call_id": c.id, "content": json.dumps({"note": note})})
                    else:
                        retried.add(c.name)
                        yield {"type": "chat.tool", "name": c.name, "ok": False, "summary": str(e)}
                        msgs.append({"role": "tool", "tool_call_id": c.id, "content": f"Error. {e}"})
    except ProviderError as e:
        yield {"type": "error", "message": str(e)}
        yield {"type": "chat.done"}


def _summ(name: str, out) -> str:
    if name == "arrange" and isinstance(out, dict):
        return f"Arranged {len(out.get('parts', []))} parts"
    if name in ("edit_part", "regenerate_part") and isinstance(out, dict):
        return f"Updated {out.get('role')} ({out.get('pattern')})"
    return name.replace("_", " ").capitalize()


async def _apply_defaults(ctx: ToolContext, args: dict, section_id: str | None) -> str:
    plan = args.get("plan") or {}
    ids = args.get("section_ids") or ([plan["section_id"]] if plan.get("section_id") else None) or ([section_id] if section_id else None)
    ctx.session.arrange(ids, None, plan.get("style"), plan.get("dynamics", "medium"))
    return "I used the style's defaults because the plan had invalid fields."


async def _json_mode(ctx: ToolContext, provider: Provider, message: str, section_id: str | None) -> AsyncIterator[dict]:
    from .. import tools as t
    styles = json.dumps(call_tool(ctx, "list_styles", {}))[:4000]
    summary = json.dumps(call_tool(ctx, "get_session", {}))[:4000]
    msgs = [{"role": "system", "content": JSON_MODE_PROMPT + styles},
            {"role": "user", "content": f"Song: {summary}\nSelected section: {section_id}\nRequest: {message}"}]
    res = await provider.chat(msgs, [])
    plan = _extract_json(res.content)
    if plan is None:
        yield {"type": "chat.delta", "text": "I couldn't read a plan from the model. Try rephrasing."}
        return
    try:
        out = call_tool(ctx, "arrange", {"plan": plan})
        yield {"type": "chat.tool", "name": "arrange", "ok": True, "summary": _summ("arrange", out)}
        yield {"type": "chat.delta", "text": "Done."}
    except ToolError:
        note = await _apply_defaults(ctx, {"plan": plan}, section_id)
        yield {"type": "chat.tool", "name": "arrange", "ok": True, "summary": note}
        yield {"type": "chat.delta", "text": note}
