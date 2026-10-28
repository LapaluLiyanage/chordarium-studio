from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import httpx


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ChatResult:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    supports_tools: bool = True


@dataclass
class ProviderHealth:
    ok: bool
    detail: str = ""
    models: list[str] = field(default_factory=list)


class ProviderError(RuntimeError):
    pass


class Provider(Protocol):
    name: str

    async def chat(self, messages: list[dict], tools: list[dict]) -> ChatResult: ...
    async def health(self) -> ProviderHealth: ...


class RulesOnlyProvider:
    """No network. The chat loop routes messages to fallback.apply_rules instead of a model."""
    name = "rules"

    async def chat(self, messages: list[dict], tools: list[dict]) -> ChatResult:  # pragma: no cover - never called
        raise ProviderError("rules-only provider has no model")

    async def health(self) -> ProviderHealth:
        return ProviderHealth(True, "Rules only (no AI)")


class OpenAICompatibleProvider:
    """Ollama, LM Studio, Gemini, Groq, OpenRouter, Mistral via their OpenAI-compatible endpoints."""

    def __init__(self, name: str, base_url: str, api_key: str | None, model: str,
                 timeout: float = 60.0, client: httpx.AsyncClient | None = None):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._client = client

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def _request(self, method: str, path: str, **kw) -> httpx.Response:
        try:
            if self._client is not None:
                return await self._client.request(method, self.base_url + path, headers=self._headers(),
                                                  timeout=self.timeout, **kw)
            async with httpx.AsyncClient() as c:
                return await c.request(method, self.base_url + path, headers=self._headers(), timeout=self.timeout, **kw)
        except httpx.HTTPError as e:
            raise ProviderError(f"Can't reach {self.name}: {e}") from e

    async def chat(self, messages: list[dict], tools: list[dict]) -> ChatResult:
        body: dict = {"model": self.model, "messages": messages}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        r = await self._request("POST", "/chat/completions", json=body)
        if r.status_code == 429:
            raise ProviderError(f"{self.name} limit reached. Try again in a minute or switch provider.")
        if r.status_code in (400, 404, 422) and tools and "tool" in r.text.lower():
            return ChatResult(supports_tools=False)
        if r.status_code >= 400:
            raise ProviderError(f"{self.name} error {r.status_code}: {r.text[:200]}")
        msg = r.json()["choices"][0]["message"]
        calls = []
        for tc in msg.get("tool_calls") or []:
            raw = tc["function"].get("arguments") or "{}"
            try:
                args = raw if isinstance(raw, dict) else __import__("json").loads(raw)
            except ValueError:
                args = {}
            calls.append(ToolCall(tc.get("id") or f"call_{len(calls)}", tc["function"]["name"], args))
        return ChatResult(content=msg.get("content") or "", tool_calls=calls)

    async def health(self) -> ProviderHealth:
        try:
            r = await self._request("GET", "/models")
        except ProviderError as e:
            return ProviderHealth(False, str(e))
        if r.status_code in (401, 403):
            return ProviderHealth(False, "The API key was rejected.")
        if r.status_code >= 400:
            return ProviderHealth(False, f"HTTP {r.status_code}")
        data = r.json().get("data") or r.json().get("models") or []
        models = [m.get("id") or m.get("name", "") for m in data if isinstance(m, dict)]
        return ProviderHealth(True, "Connected", models)
