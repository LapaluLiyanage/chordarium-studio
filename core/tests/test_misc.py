import pytest

from chordarium_core import config
from chordarium_core.remote import RemoteError, RemoteOut
from chordarium_core.session import Session, SessionError, suggest_style


def test_config_and_token(tmp_path):
    t1, t2 = config.get_token(tmp_path), config.get_token(tmp_path)
    assert t1 == t2 and len(t1) == 64
    cfg = config.Config(provider="ollama")
    assert cfg.resolved_base_url() == "http://127.0.0.1:11434/v1"
    assert config.Config(provider="x", base_url="http://h/v1").resolved_base_url() == "http://h/v1"
    config.save_config(cfg, tmp_path)
    assert config.load_config(tmp_path).provider == "ollama"
    (tmp_path / "config.json").write_text("{bad")
    assert config.load_config(tmp_path).provider == "rules"


def test_data_dir_env(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORDARIUM_HOME", str(tmp_path / "h"))
    assert config.data_dir() == tmp_path / "h" and (tmp_path / "h").exists()
    monkeypatch.delenv("CHORDARIUM_HOME")
    monkeypatch.setenv("APPDATA", str(tmp_path / "ad"))
    assert config.data_dir() == tmp_path / "ad" / "ChordariumStudio"
    monkeypatch.delenv("APPDATA")


def test_keyring_failures_are_safe(monkeypatch):
    import keyring
    monkeypatch.setattr(keyring, "set_password", lambda *a: (_ for _ in ()).throw(RuntimeError("no backend")))
    monkeypatch.setattr(keyring, "get_password", lambda *a: (_ for _ in ()).throw(RuntimeError("no backend")))
    assert config.set_api_key("groq", "k") is False and config.get_api_key("groq") is None


def test_remote_errors():
    r = RemoteOut(port=type("P", (), {"send_message": lambda s, m: None})())
    with pytest.raises(RemoteError):
        r.send("explode")
    assert RemoteOut("nothing").available() is False


def test_session_guards():
    s = Session()
    with pytest.raises(SessionError):
        s.require_song()
    s.load_sheet("| C | F |")
    with pytest.raises(SessionError):
        s.part_for("sec_other_1", "bass")
    with pytest.raises(SessionError):
        s.edit_part("sec_other_1", "bass", {})
    s.arrange(None)
    with pytest.raises(SessionError):
        s.edit_part(None, "bass", {"role": "piano"})
    assert s.summary()["parts"]
    assert suggest_style(s.song) == "pop_4_4"
    s6 = Session()
    s6.load_sheet("Time: 6/8\n| C | F |")
    assert suggest_style(s6.song) == "baila_6_8"
    ssi = Session()
    ssi.load_sheet("| C | F |\nසඳ")
    assert suggest_style(ssi.song) == "sinhala_ballad"
    s.load_sheet("| C | F |")
    for _ in range(3):
        s.arrange(None)
    assert len(s.undo_stack) >= 3
