"""Simple JSON-backed settings store for LLM provider config."""

import json
from typing import Any

from .config import settings

DEFAULT_SETTINGS = {
    "provider": "ollama",
    "base_url": "http://127.0.0.1:11434",
    "model": "",
    "api_key": "",
    "timeout": 60,
    "coworker_timezone": "Europe/Vienna",
    "fleet_pulse_time": "07:00",
    "fleet_repos_root": "D:/Dev/repos",
    "fleet_pulse_repos": ["fleet-agent-mcp", "mcp-central-docs"],
    "heartbeat_email": "",
    "fleet_pulse_email": "",
    "smtp_host": "",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_pass": "",
    "artifact_pack_glob": "*.md",
    "artifact_pack_max_files": 20,
    "urgent_email_enabled": True,
    "urgent_email_threshold": 8.0,
    "devices_mcp_http_base": "http://127.0.0.1:10717",
    "coworker_devices_watch_enabled": True,
    "devices_watch_interval": "5m",
}

PROVIDER_PRESETS = {
    "ollama": {"base_url": "http://127.0.0.1:11434"},
    "lmstudio": {"base_url": "http://127.0.0.1:1234"},
}


class SettingsStore:
    def __init__(self) -> None:
        self._path = settings.data_dir / "settings.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return dict(DEFAULT_SETTINGS)

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._save()

    def get_all(self) -> dict[str, Any]:
        return dict(self._data)

    def update(self, updates: dict[str, Any]) -> dict[str, Any]:
        self._data.update(updates)
        self._save()
        return self.get_all()


_store: SettingsStore | None = None


def get_settings_store() -> SettingsStore:
    global _store
    if _store is None:
        _store = SettingsStore()
    return _store
