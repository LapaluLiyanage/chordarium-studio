import json

import pytest
from conftest import SHEET, TOKEN
from fastapi.testclient import TestClient

from chordarium_core.session import Session


def test_health_open_but_rest_needs_token(env):
    assert env.c.get("/health", headers={}).json()["status"] == "ok"
    bare = TestClient(env.app)
    assert bare.get("/session").status_code == 401
    assert bare.get("/session", headers={"X-Chordarium-Token": "nope"}).status_code == 401


def test_parse_session_styles_select(env):
    assert env.c.get("/session").json()["song"] is None
    assert env.c.post("/song/parse", json={"text": "  "}).status_code == 422
    song = env.c.post("/song/parse", json={"text": SHEET}).json()
    assert song["title"] == "Test Song" and len(song["sections"]) == 2
    s = env.c.get("/session").json()
    assert s["selected_section_id"] == "sec_verse_1" and s["song"]["sections"][1]["chords"][1] == ["Em", "C"]
    st = env.c.get("/styles").json()
    assert {x["id"] for x in st["styles"]} >= {"pop_4_4", "sinhala_ballad"}
    assert env.c.post("/select", json={"section_id": "Chorus 1"}).json()["selected_section_id"] == "sec_chorus_1"
    assert env.c.post("/select", json={"section_id": "zzz"}).status_code == 400


def test_arrange_edit_regenerate_lock_clear(loaded):
    c = loaded.c
    r = c.post("/arrange", json={"section_ids": ["sec_chorus_1"], "style": "sinhala_ballad", "dynamics": "soft"}).json()
    assert [p["role"] for p in r["parts"]] == ["piano", "bass", "pad", "drums"]
    pid = "part_sec_chorus_1_piano"
    full = c.get(f"/parts/{pid}").json()
    assert full["notes"] and full["channel"] == 1
    assert c.get("/parts/nope").status_code == 404
    e = c.post(f"/parts/{pid}/edit", json={"pattern": "block", "density": 0.9}).json()
    assert e["spec"]["pattern"] == "block" and e["seed"] == full["seed"]
    assert c.post(f"/parts/{pid}/edit", json={"pattern": "nonsense"}).status_code == 422
    g = c.post(f"/parts/{pid}/regenerate", json={"seed": 77}).json()
    assert g["seed"] == 77
    assert c.post(f"/parts/{pid}/regenerate").json()["seed"] != 77
    assert c.post(f"/parts/{pid}/lock", json={"locked": True}).json()["locked"] is True
    assert c.post(f"/parts/{pid}/edit", json={"density": 0.1}).status_code == 400
    # locked parts survive a re-arrange untouched
    before = c.get(f"/parts/{pid}").json()
    c.post("/arrange", json={"section_ids": ["sec_chorus_1"], "style": "pop_4_4"})
    assert c.get(f"/parts/{pid}").json() == before
    c.post(f"/parts/{pid}/lock", json={"locked": False})
    assert c.delete(f"/parts/{pid}").json()["ok"] is True
    assert c.get(f"/parts/{pid}").status_code == 404


def test_invalid_plan_422(loaded):
    plan = {"style": "pop_4_4", "parts": [{"role": "bass", "pattern": "nope"}]}
    r = loaded.c.post("/arrange", json={"section_ids": ["sec_chorus_1"], "plan": plan})
    assert r.status_code == 400 and "Fix these fields" in r.json()["detail"]


def test_patch_song_regenerates_changed_sections(loaded):
    c = loaded.c
    c.post("/arrange", json={"section_ids": ["sec_chorus_1"]})
    before = c.get("/parts/part_sec_chorus_1_bass").json()
    sec = c.get("/session/snapshot").json()["song"]["sections"][1]
    sec["bars"][0]["chords"][0]["symbol"] = "C"
    c.patch("/song", json={"tempo_bpm": 90, "sections": [c.get("/session/snapshot").json()["song"]["sections"][0], sec]})
    after = c.get("/parts/part_sec_chorus_1_bass").json()
    assert after["notes"] != before["notes"]
    assert c.get("/session").json()["song"]["tempo_bpm"] == 90
    # removing a section drops its parts
    c.patch("/song", json={"sections": [c.get("/session/snapshot").json()["song"]["sections"][0]]})
    assert c.get("/parts/part_sec_chorus_1_bass").status_code == 404


def test_undo_redo(loaded):
    c = loaded.c
    c.post("/arrange", json={"section_ids": ["sec_chorus_1"]})
    assert c.get("/parts/part_sec_chorus_1_piano").status_code == 200
    assert c.post("/undo").json()["ok"] is True
    assert c.get("/parts/part_sec_chorus_1_piano").status_code == 404
    assert c.post("/redo").json()["ok"] is True
    assert c.get("/parts/part_sec_chorus_1_piano").status_code == 200
    s = Session()
    assert s.undo() is False and s.redo() is False


def test_export_scopes(loaded):
    c = loaded.c
    assert c.post("/export", json={"scope": "section"}).status_code == 400  # not arranged
    c.post("/arrange", json={"section_ids": ["sec_chorus_1"]})
    f = c.post("/export", json={"scope": "section", "ids": ["sec_chorus_1"]}).json()["files"]
    assert f[0].endswith("Chorus1.mid")
    p = c.post("/export", json={"scope": "part", "ids": ["part_sec_chorus_1_bass"]}).json()["files"]
    assert p[0].endswith("Chorus1_Bass.mid")
    assert c.post("/export", json={"scope": "song"}).json()["files"][0].endswith(".mid")
    assert c.post("/export", json={"scope": "part"}).status_code == 400
    assert c.post("/export", json={"scope": "bogus"}).status_code == 400
    assert c.post("/export", json={"scope": "part", "ids": ["x"]}).status_code == 400


def test_remote_transport(env):
    assert env.c.post("/remote/play").json()["ok"] is True
    assert env.port.sent[-1] == [0xBF, 20, 127]
    env.c.post("/remote/add_marker")
    assert env.port.sent[-1][1] == 24
    assert env.c.post("/remote/explode").status_code == 409
    assert env.c.get("/health").json()["cubase_remote"] is True


def test_remote_unavailable_message(tmp_path):
    from chordarium_core.app import create_app
    from chordarium_core.remote import RemoteOut
    app = create_app(home=tmp_path, remote=RemoteOut("No Such Port"), token=TOKEN)
    c = TestClient(app, headers={"X-Chordarium-Token": TOKEN})
    r = c.post("/remote/play")
    assert r.status_code == 409 and "Cubase link not set up" in r.json()["detail"]
    assert c.get("/health").json()["cubase_remote"] is False


def test_tools_endpoint_matches_registry(env):
    t = env.c.get("/tools").json()
    assert {x["name"] for x in t["tools"]} == {"get_session", "load_chord_sheet", "list_styles", "arrange", "edit_part",
                                               "regenerate_part", "set_part_lock", "export_midi", "transport"}
    assert len(t["openai"]) == 9 and t["openai"][0]["type"] == "function"
    assert env.c.post("/tools/get_session", json={}).status_code == 200
    assert env.c.post("/tools/nope", json={}).status_code == 404
    assert env.c.post("/tools/load_chord_sheet", json={}).status_code == 400


def test_config_roundtrip_hides_key(env, monkeypatch):
    stored = {}
    monkeypatch.setattr("chordarium_core.app.set_api_key", lambda p, k: stored.setdefault(p, k) and True)
    monkeypatch.setattr("chordarium_core.app.get_api_key", lambda p: stored.get(p))
    r = env.c.put("/config", json={"provider": "groq", "model": "llama", "api_key": "sk-secret"}).json()
    assert r["provider"] == "groq" and r["has_key"] is True and "sk-secret" not in json.dumps(r)
    assert "sk-secret" not in (env.home / "config.json").read_text()
    got = env.c.get("/config").json()
    assert got["model"] == "llama" and "api_key" not in got and got["has_key"] is True
    monkeypatch.setattr("chordarium_core.app.set_api_key", lambda p, k: False)
    assert env.c.put("/config", json={"api_key": "x"}).status_code == 500


def test_provider_test_endpoint(env):
    r = env.c.post("/provider/test").json()
    assert r["ok"] is True


def test_session_persistence_and_snapshot_restore(loaded):
    loaded.c.post("/arrange", json={"section_ids": ["sec_chorus_1"]})
    f = loaded.home / "sessions"
    # debounced save runs in the event loop; force a sync save for the test
    loaded.app.state.session.save(loaded.home)
    saved = next(f.glob("*.json"))
    s2 = Session.load(saved)
    assert s2.song.title == "Test Song" and "part_sec_chorus_1_piano" in s2.parts
    snap = loaded.c.get("/session/snapshot").json()
    loaded.c.post("/song/parse", json={"text": "| C | F |"})
    assert loaded.c.put("/session/snapshot", json=snap).json()["song"]["title"] == "Test Song"


def test_websocket_auth_events_and_preview(loaded):
    c = loaded.c
    with pytest.raises(Exception):
        with c.websocket_connect("/ws") as bad:
            bad.send_json({"type": "hello", "token": "wrong"})
            bad.receive_json()
    with c.websocket_connect("/ws") as ws:
        ws.send_json({"type": "hello", "client": "ui", "token": TOKEN})
        assert ws.receive_json()["type"] == "hello.ok"
        c.post("/arrange", json={"section_ids": ["sec_chorus_1"]})
        ev = ws.receive_json()
        assert ev["type"] == "session.updated" and ev["session"]["parts"]
        c.post("/parts/part_sec_chorus_1_bass/regenerate", json={"seed": 5})
        assert ws.receive_json()["type"] == "part.updated"
        ws.send_json({"type": "preview.request", "section_id": "sec_chorus_1"})
        while True:
            m = ws.receive_json()
            if m["type"] == "preview.parts":
                break
        assert len(m["parts"]) == 4 and m["parts"][0]["notes"]
