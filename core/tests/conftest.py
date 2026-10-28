import os
import pytest
from fastapi.testclient import TestClient

from chordarium_core.app import create_app
from chordarium_core.remote import RemoteOut

SHEET = "Title: Test Song\nKey: G\nTempo: 76\n[Verse 1]\n| Em | C | G | D |\n[Chorus 1]\n| G | Em C | D | G |"
TOKEN = "t" * 64


class FakePort:
    def __init__(self):
        self.sent = []

    def send_message(self, m):
        self.sent.append(m)


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORDARIUM_HOME", str(tmp_path))
    port = FakePort()
    providers = {}
    app = create_app(home=tmp_path, remote=RemoteOut(port=port), token=TOKEN,
                     provider_factory=lambda cfg: providers.get("p") or __import__("chordarium_core.ai.providers", fromlist=["x"]).RulesOnlyProvider())
    client = TestClient(app, headers={"X-Chordarium-Token": TOKEN})
    return type("Env", (), {"app": app, "c": client, "port": port, "home": tmp_path, "providers": providers})


@pytest.fixture
def loaded(env):
    assert env.c.post("/song/parse", json={"text": SHEET}).status_code == 200
    return env
