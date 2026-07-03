"""v2 hook: authenticated crawling. Not implemented in v1 (see build plan Phase 8).

Design intent, so v2 slots in without a pipeline rewrite:

- A user supplies either `--auth-state <path>` (a Playwright `storageState` JSON —
  cookies + localStorage captured from a real logged-in session) or
  `--login-script <path>` (a short script this tool runs once to fill credentials,
  submit, and wait for the post-login redirect).
- Either path produces a Playwright `BrowserContext` seeded with authenticated
  state. `crawler.py` and `endpoints.py` would accept that context as an optional
  parameter instead of always creating a fresh anonymous one.
- `reporting/coverage.py` already tracks "not reached" pages with a reason string
  (see `UnreachedPage`) and a `public_only` flag on `CoverageSummary`. Turning that
  flag off and wiring an authenticated context through turns currently-unreached
  auth-gated pages into tested ones, without changing the coverage data model.

v1 intentionally does not guess at authenticated behavior: pages requiring login
are reported as not covered (see `Config.public_only` in config.py), never silently
skipped or falsely marked as passing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class AuthConfig:
    storage_state_path: Path | None = None
    login_script_path: Path | None = None

    @property
    def enabled(self) -> bool:
        return self.storage_state_path is not None or self.login_script_path is not None


async def build_authenticated_context(browser, auth: AuthConfig):
    """Not implemented in v1 — fails loudly rather than silently crawling anonymously."""
    raise NotImplementedError(
        "Authenticated crawling is a v2 feature (build plan Phase 8). "
        "v1 reports auth-gated areas as not covered instead of pretending to test them."
    )
