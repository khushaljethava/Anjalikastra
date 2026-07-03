"""Store and diff a structural baseline (DOM shape + screenshot) per page.

Baselines persist across runs so a re-run against an unchanged site can prove zero
regressions, and a deliberately changed element shows up as a diff. Volatile regions
(timestamps, relative-time strings, common ad/rotating-banner containers) are
normalized out before hashing — the exact false-positive sources Phase 5 calls out.
Whatever noise survives normalization is left for Phase 7's triage step to classify
as flake/expected-change rather than a hard regression gate here.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from playwright.async_api import Page

logger = logging.getLogger("anjalikastra.execution.baseline")

_VOLATILE_PATTERNS = [
    re.compile(r"\d{4}-\d{2}-\d{2}T[\d:.]+Z?"),  # ISO timestamps
    re.compile(r"\b\d{1,2}:\d{2}(:\d{2})?\s?(AM|PM|am|pm)?\b"),  # clock times
    re.compile(r"\b(a|an|\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago\b", re.I),  # relative time
    re.compile(r'data-testid="[^"]*(ad|banner|promo)[^"]*"', re.I),  # ad/banner containers
]


def _normalize(html: str) -> str:
    for pattern in _VOLATILE_PATTERNS:
        html = pattern.sub("[VOLATILE]", html)
    return html


@dataclass
class PageBaseline:
    url: str
    structure_hash: str
    screenshot_path: str
    captured_at: str


@dataclass
class DiffResult:
    url: str
    changed: bool
    previous_hash: str | None
    current_hash: str


class BaselineStore:
    """Persists baselines under `<output-dir>/.baseline/`, independent of any single run."""

    def __init__(self, baseline_dir: Path):
        self.baseline_dir = baseline_dir
        self.baseline_dir.mkdir(parents=True, exist_ok=True)
        (self.baseline_dir / "screenshots").mkdir(exist_ok=True)

    def _index_path(self) -> Path:
        return self.baseline_dir / "index.json"

    def _load_index(self) -> dict[str, dict]:
        path = self._index_path()
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            logger.warning("baseline index corrupt; starting fresh")
            return {}

    def _save_index(self, index: dict[str, dict]) -> None:
        self._index_path().write_text(json.dumps(index, indent=2))

    async def capture(self, page: Page, url: str) -> PageBaseline:
        import datetime

        html = await page.content()
        normalized = _normalize(html)
        structure_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

        screenshot_name = hashlib.sha256(url.encode()).hexdigest()[:16] + ".png"
        screenshot_path = self.baseline_dir / "screenshots" / screenshot_name
        await page.screenshot(path=str(screenshot_path), full_page=True)

        return PageBaseline(
            url=url,
            structure_hash=structure_hash,
            screenshot_path=str(screenshot_path),
            captured_at=datetime.datetime.utcnow().isoformat() + "Z",
        )

    def diff_and_store(self, baseline: PageBaseline) -> DiffResult:
        index = self._load_index()
        previous = index.get(baseline.url)
        previous_hash = previous.get("structure_hash") if previous else None
        changed = previous_hash is not None and previous_hash != baseline.structure_hash

        index[baseline.url] = asdict(baseline)
        self._save_index(index)

        return DiffResult(
            url=baseline.url, changed=changed, previous_hash=previous_hash, current_hash=baseline.structure_hash
        )
