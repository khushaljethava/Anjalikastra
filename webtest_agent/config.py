"""Centralized settings: model names, thresholds, caps. Every tunable lives here."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    url: str
    output_dir: Path = Path("output")
    run_id: str | None = None

    # Discovery
    max_pages: int = 40
    throttle_ms: int = 500
    public_only: bool = True
    openapi_path: Path | None = None
    respect_robots: bool = True
    classification_concurrency: int = 5  # bounded concurrent LLM calls; site requests are never parallelized

    # Models (cheap for classification/summaries, capable for generation/triage).
    # Defaults can be overridden by env vars or the --cheap-model/--capable-model CLI flags.
    cheap_model: str = field(default_factory=lambda: os.environ.get("WEBTEST_AGENT_CHEAP_MODEL", "claude-haiku-4-5-20251001"))
    capable_model: str = field(default_factory=lambda: os.environ.get("WEBTEST_AGENT_CAPABLE_MODEL", "claude-sonnet-5"))
    # "anthropic", "openai" (any OpenAI-compatible endpoint: OpenAI, Ollama,
    # OpenRouter, Gemini, vLLM, ...), or None to auto-detect from credentials.
    llm_provider: str | None = field(default_factory=lambda: os.environ.get("WEBTEST_AGENT_LLM_PROVIDER") or None)
    llm_max_retries: int = 2

    # Generation
    load_time_threshold_ms: int = 5000

    # Execution
    playwright_timeout_ms: int = 30_000

    # Misc
    dry_run: bool = False
    verbose: bool = False
    user_agent: str = "webtest-agent/0.1 (+https://github.com/webtest-agent/webtest-agent)"

    cache_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)
        if self.run_id is None:
            import time

            self.run_id = time.strftime("%Y%m%d-%H%M%S")
        self.cache_dir = self.output_dir / ".cache"

    @property
    def run_dir(self) -> Path:
        return self.output_dir / self.run_id

    @property
    def suite_dir(self) -> Path:
        return self.run_dir / "suite"

    @property
    def resolved_llm_provider(self) -> str | None:
        """The provider a run would actually use ("anthropic"/"openai"), or None
        when nothing is configured and the heuristic fallback applies."""
        from webtest_agent.llm.client import resolve_provider

        return resolve_provider(self.llm_provider)

    @property
    def chromium_executable_path(self) -> str | None:
        """Optional override for environments with a pre-installed Chromium binary
        (offline installs, CI images) instead of one downloaded by `playwright install`."""
        return os.environ.get("WEBTEST_AGENT_CHROMIUM_PATH") or None
