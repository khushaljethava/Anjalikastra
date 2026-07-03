"""Run checkpointing so a crashed run can resume instead of restarting from scratch.

Scoped to the phase that's most expensive to redo and least idempotent by
default: discovery. Re-crawling and re-capturing endpoint traffic after every
crash means hitting the target's real infrastructure again — exactly the load
the throttle exists to bound — so a crash partway through a large crawl
shouldn't force starting over. Classification/generation are already cheap to
redo across runs via the content-hash cache in cache/store.py, so they don't
need a separate checkpoint.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("webtest_agent.checkpoint")


class Checkpoint:
    def __init__(self, run_dir: Path):
        self.path = run_dir / "checkpoint.json"
        self._data: dict[str, Any] = {}
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text())
            except json.JSONDecodeError:
                logger.warning("checkpoint file at %s is corrupt; ignoring it", self.path)

    def has(self, stage: str) -> bool:
        return stage in self._data

    def get(self, stage: str) -> Any | None:
        return self._data.get(stage)

    def save(self, stage: str, payload: Any) -> None:
        self._data[stage] = payload
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2, default=str))
        logger.info("checkpoint: saved stage=%s", stage)
