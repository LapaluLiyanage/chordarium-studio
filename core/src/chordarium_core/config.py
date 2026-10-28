"""Config, local auth token and API-key storage (spec 9.4). Keys never touch config.json or logs."""
from __future__ import annotations

import json
import os
import secrets
from pathlib import Path

from pydantic import BaseModel

APP_DIR = "ChordariumStudio"

PRESETS: dict[str, dict[str, str]] = {  # [VERIFY] at implementation time; kept in config, not code paths
    "ollama": {"base_url": "http://127.0.0.1:11434/v1"},
    "lmstudio": {"base_url": "http://127.0.0.1:1234/v1"},
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/"},
    "groq": {"base_url": "https://api.groq.com/openai/v1"},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1"},
    "mistral": {"base_url": "https://api.mistral.ai/v1"},
}


class Config(BaseModel):
    provider: str = "rules"  # rules | mcp | custom | one of PRESETS
    model: str = ""
    base_url: str = ""
    port: int = 47811
    cubase_port_name: str = "Chordarium Remote"

    def resolved_base_url(self) -> str:
        return self.base_url or PRESETS.get(self.provider, {}).get("base_url", "")


def data_dir() -> Path:
    if os.environ.get("CHORDARIUM_HOME"):
        p = Path(os.environ["CHORDARIUM_HOME"])
    elif os.environ.get("APPDATA"):
        p = Path(os.environ["APPDATA"]) / APP_DIR
    else:
        p = Path.home() / ".local" / "share" / APP_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_config(home: Path | None = None) -> Config:
    f = (home or data_dir()) / "config.json"
    if f.exists():
        try:
            return Config.model_validate_json(f.read_text(encoding="utf-8"))
        except ValueError:
            pass
    return Config()


def save_config(cfg: Config, home: Path | None = None) -> None:
    f = (home or data_dir()) / "config.json"
    f.write_text(cfg.model_dump_json(indent=2), encoding="utf-8")


def get_token(home: Path | None = None) -> str:
    f = (home or data_dir()) / "token"
    if f.exists() and f.read_text().strip():
        return f.read_text().strip()
    tok = secrets.token_hex(32)
    f.write_text(tok)
    try:
        f.chmod(0o600)
    except OSError:
        pass
    return tok


def set_api_key(provider: str, key: str) -> bool:
    try:
        import keyring
        keyring.set_password("ChordariumStudio", provider, key)
        return True
    except Exception:
        return False


def get_api_key(provider: str) -> str | None:
    try:
        import keyring
        return keyring.get_password("ChordariumStudio", provider)
    except Exception:
        return None
