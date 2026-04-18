from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional


class PostHistory:
    def __init__(self, path: str) -> None:
        self._path = path
        self._entries: list[dict] = []
        self._ids: set[str] = set()
        if os.path.exists(path):
            self._load()

    @property
    def used_ids(self) -> set[str]:
        return self._ids

    def contains(self, post_id: str) -> bool:
        return post_id in self._ids

    def record(
        self,
        post_id: str,
        title: str,
        url: str,
        run_id: str,
    ) -> None:
        if post_id in self._ids:
            return
        entry = {
            "post_id": post_id,
            "title": title,
            "url": url,
            "used_at": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
        }
        self._entries.append(entry)
        self._ids.add(post_id)
        self._save()

    def clear(self) -> None:
        self._entries = []
        self._ids = set()
        self._save()

    def _load(self) -> None:
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
            self._entries = data.get("entries", [])
            self._ids = {e["post_id"] for e in self._entries if "post_id" in e}
        except (json.JSONDecodeError, OSError):
            self._entries = []
            self._ids = set()

    def _save(self) -> None:
        parent = os.path.dirname(os.path.abspath(self._path))
        os.makedirs(parent, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump({"entries": self._entries}, f, indent=2, ensure_ascii=False)
