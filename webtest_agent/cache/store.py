"""DOM/classification/assertion cache keyed by URL + content-hash.

Persists across runs (lives under `<output-dir>/.cache`, not the per-run directory)
so a second run against an unchanged site can skip re-classifying and re-generating
assertions for pages whose content hasn't moved — the core of Phase 6's token savings.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("webtest_agent.cache")


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0

    def __str__(self) -> str:
        total = self.hits + self.misses
        rate = (self.hits / total * 100) if total else 0
        return f"{self.hits}/{total} cache hits ({rate:.0f}%)"


class CacheStore:
    """One JSON file per namespace: {url: {"hash": ..., "value": ...}}."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.stats = CacheStats()
        self._data: dict[str, dict[str, dict[str, Any]]] = {}

    def _path(self, namespace: str) -> Path:
        return self.cache_dir / f"{namespace}.json"

    def _load(self, namespace: str) -> dict[str, dict[str, Any]]:
        if namespace not in self._data:
            path = self._path(namespace)
            if path.exists():
                try:
                    self._data[namespace] = json.loads(path.read_text())
                except json.JSONDecodeError:
                    logger.warning("cache file %s is corrupt; starting fresh", path)
                    self._data[namespace] = {}
            else:
                self._data[namespace] = {}
        return self._data[namespace]

    def get(self, namespace: str, key: str, current_hash: str) -> Any | None:
        entry = self._load(namespace).get(key)
        if entry and entry.get("hash") == current_hash:
            self.stats.hits += 1
            return entry.get("value")
        self.stats.misses += 1
        return None

    def set(self, namespace: str, key: str, current_hash: str, value: Any) -> None:
        self._load(namespace)[key] = {"hash": current_hash, "value": value}

    def flush(self) -> None:
        for namespace, entries in self._data.items():
            self._path(namespace).write_text(json.dumps(entries, indent=2))
