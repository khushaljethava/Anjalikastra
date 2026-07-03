"""Model calls with cheap-vs-capable routing and per-call token usage logging.

Two provider backends:

- ``anthropic`` — the Anthropic Messages API (Claude models), via the official SDK.
- ``openai`` — any OpenAI-compatible Chat Completions endpoint. This one setting
  covers OpenAI itself, Ollama (local models), OpenRouter, Gemini's OpenAI-compat
  endpoint, vLLM, LM Studio, and anything else that speaks the same protocol:
  point ``OPENAI_BASE_URL`` at the server and pass its model names.

The provider is picked explicitly via ``WEBTEST_AGENT_LLM_PROVIDER`` (or the
``--llm-provider`` flag), or auto-detected from which credentials are present.
When neither backend is configured, ``complete()`` raises ``LLMUnavailable`` so
callers fall back to their heuristic path — the tool stays usable, with reduced
quality, without any LLM at all.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Literal

logger = logging.getLogger("webtest_agent.llm")

ModelTier = Literal["cheap", "capable"]

PROVIDERS = ("anthropic", "openai")


def resolve_provider(explicit: str | None = None) -> str | None:
    """Pick the LLM backend: explicit setting first, then auto-detect from env.

    Auto-detection order matters only when both providers are configured;
    Anthropic wins the tie because it's the tool's native default.
    """
    provider = (explicit or os.environ.get("WEBTEST_AGENT_LLM_PROVIDER") or "").lower() or None
    if provider is not None:
        if provider not in PROVIDERS:
            raise ValueError(f"unknown LLM provider {provider!r}; expected one of {PROVIDERS}")
        return provider
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_BASE_URL"):
        return "openai"
    return None


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, input_tokens: int, output_tokens: int) -> None:
        self.calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def __str__(self) -> str:
        return f"{self.calls} calls, {self.input_tokens} in / {self.output_tokens} out tokens"


@dataclass
class TokenLedger:
    """Tracks usage per tier so a run can report cost and prove Phase 6's cache savings."""

    cheap: Usage = field(default_factory=Usage)
    capable: Usage = field(default_factory=Usage)

    def record(self, tier: ModelTier, input_tokens: int, output_tokens: int) -> None:
        getattr(self, tier).add(input_tokens, output_tokens)

    def summary(self) -> str:
        return f"cheap model: {self.cheap} | capable model: {self.capable}"


class LLMClient:
    """Tier-routing wrapper over the configured provider SDK."""

    def __init__(
        self,
        cheap_model: str,
        capable_model: str,
        ledger: TokenLedger | None = None,
        provider: str | None = None,
    ):
        self.cheap_model = cheap_model
        self.capable_model = capable_model
        self.ledger = ledger or TokenLedger()
        self.provider = resolve_provider(provider)
        self._client = None

        if self.provider == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
            import anthropic

            self._client = anthropic.Anthropic()
        elif self.provider == "openai":
            from openai import OpenAI

            # Local servers like Ollama accept any non-empty key; only a real
            # OpenAI/OpenRouter/Gemini endpoint will reject the placeholder.
            self._client = OpenAI(
                base_url=os.environ.get("OPENAI_BASE_URL") or None,
                api_key=os.environ.get("OPENAI_API_KEY", "unused"),
            )

    @property
    def available(self) -> bool:
        return self._client is not None

    def complete(self, tier: ModelTier, system: str, prompt: str, max_tokens: int = 4096) -> str:
        if not self._client:
            raise LLMUnavailable(
                "No LLM backend configured. Set ANTHROPIC_API_KEY, or OPENAI_API_KEY / "
                "OPENAI_BASE_URL for an OpenAI-compatible endpoint (OpenAI, Ollama, "
                "OpenRouter, Gemini, ...)."
            )

        model = self.cheap_model if tier == "cheap" else self.capable_model
        try:
            if self.provider == "anthropic":
                text, input_tokens, output_tokens = self._complete_anthropic(model, system, prompt, max_tokens)
            else:
                text, input_tokens, output_tokens = self._complete_openai(model, system, prompt, max_tokens)
        except Exception as exc:
            # Provider/network errors degrade that one call to the caller's
            # heuristic fallback instead of crashing the whole run.
            raise LLMUnavailable(f"LLM call failed ({self.provider}, model={model}): {exc}") from exc

        self.ledger.record(tier, input_tokens, output_tokens)
        logger.info(
            "llm_call provider=%s tier=%s model=%s input_tokens=%d output_tokens=%d",
            self.provider, tier, model, input_tokens, output_tokens,
        )
        return text

    def _complete_anthropic(self, model: str, system: str, prompt: str, max_tokens: int) -> tuple[str, int, int]:
        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return text, response.usage.input_tokens, response.usage.output_tokens

    def _complete_openai(self, model: str, system: str, prompt: str, max_tokens: int) -> tuple[str, int, int]:
        response = self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        text = response.choices[0].message.content or ""
        usage = response.usage  # some compatible servers omit usage entirely
        input_tokens = getattr(usage, "prompt_tokens", 0) or 0
        output_tokens = getattr(usage, "completion_tokens", 0) or 0
        return text, input_tokens, output_tokens

    async def acomplete(self, tier: ModelTier, system: str, prompt: str, max_tokens: int = 4096) -> str:
        """Async wrapper so independent classify/generate calls can run concurrently
        (bounded by a semaphore at the call site) instead of blocking the event loop
        one call at a time — the provider SDKs' sync clients do the actual I/O in
        a worker thread via `asyncio.to_thread`."""
        return await asyncio.to_thread(self.complete, tier, system, prompt, max_tokens)


class LLMUnavailable(RuntimeError):
    """Raised when no backend is configured, or a provider call fails — callers
    treat both the same way: fall back to the heuristic path for that item."""
