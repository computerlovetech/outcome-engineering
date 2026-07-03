"""CLI configuration and token storage in ~/.config/oe/."""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_API_URL = "http://localhost:8000"


def config_dir() -> Path:
    override = os.environ.get("OE_CONFIG_DIR")
    if override:
        return Path(override)
    return Path.home() / ".config" / "oe"


def _config_file() -> Path:
    return config_dir() / "config.json"


def load_config() -> dict:
    path = _config_file()
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_config(config: dict) -> None:
    path = _config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def api_url() -> str:
    return os.environ.get("OE_API_URL") or load_config().get("api_url") or DEFAULT_API_URL


def access_token() -> str | None:
    return os.environ.get("OE_TOKEN") or load_config().get("access_token")
