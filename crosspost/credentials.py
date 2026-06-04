from __future__ import annotations
import json
from pathlib import Path


class CredentialStore:
    def __init__(self, path):
        self.path = Path(path)

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def get(self, platform: str) -> dict:
        return self._load().get(platform, {})

    def set(self, platform: str, data: dict) -> None:
        all_creds = self._load()
        all_creds[platform] = data
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(all_creds, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def has(self, platform: str, required_keys: list[str]) -> bool:
        creds = self.get(platform)
        return all(creds.get(k) for k in required_keys)
