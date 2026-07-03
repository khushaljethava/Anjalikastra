"""Classify each test failure and draft a structured bug report — never auto-filed.

Bias toward flagging when uncertain: a wrong "all clear" costs trust far more than
a false alarm, so the heuristic fallback (no LLM configured) defaults to
'needs_human_review' rather than guessing a category it can't support.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from webtest_agent.execution.runner import TestResult
from webtest_agent.llm.client import LLMClient, LLMUnavailable

logger = logging.getLogger("webtest_agent.triage")

CLASSIFICATIONS = ["regression", "flake", "expected_change", "needs_human_review"]


@dataclass
class DraftBug:
    title: str
    affected: str
    classification: str
    confidence: float
    steps: str
    expected: str
    actual: str
    reasoning: str = ""


def _heuristic_classify(result: TestResult) -> tuple[str, float]:
    error = (result.error or "").lower()
    if "timeout" in error or "econnreset" in error or "net::err" in error:
        return "flake", 0.4  # low confidence — still surfaced, not silently dismissed
    return "needs_human_review", 0.3


async def triage_failure(result: TestResult, llm: LLMClient) -> DraftBug:
    classification, confidence = _heuristic_classify(result)
    reasoning = "heuristic (no LLM configured)"

    if llm.available:
        try:
            prompt = (
                f"A Playwright test failed. Classify the failure.\n"
                f"Test: {result.title}\nFile: {result.file}\n"
                f"Error: {(result.error or '')[:1500]}\n\n"
                f"Allowed classifications: {', '.join(CLASSIFICATIONS)}\n"
                "regression = the site is actually broken; flake = timing/network noise unrelated to "
                "a real defect; expected_change = the site intentionally changed since the test was "
                "generated; needs_human_review = you cannot tell from the error alone.\n"
                "If you are not confident, prefer needs_human_review over guessing.\n\n"
                'Reply with strict JSON: {"classification": "...", "confidence": 0.0-1.0, '
                '"reasoning": "one sentence", "expected": "...", "actual": "..."}'
            )
            raw = await llm.acomplete(
                "capable",
                system="You are a precise test-failure triage assistant for a QA tool. Reply with JSON only.",
                prompt=prompt,
                max_tokens=400,
            )
            parsed = json.loads(_extract_json(raw))
            classification = parsed.get("classification") if parsed.get("classification") in CLASSIFICATIONS else "needs_human_review"
            confidence = float(parsed.get("confidence", 0.5))
            reasoning = parsed.get("reasoning", "")
            return DraftBug(
                title=f"{result.title} — {classification.replace('_', ' ')}",
                affected=result.file,
                classification=classification,
                confidence=confidence,
                steps=f"Run `{result.title}` in {result.file}",
                expected=parsed.get("expected", "test passes"),
                actual=parsed.get("actual", result.error or "test failed"),
                reasoning=reasoning,
            )
        except (LLMUnavailable, json.JSONDecodeError, ValueError, KeyError) as exc:
            logger.debug("triage LLM call failed for %s, using heuristic: %s", result.title, exc)

    return DraftBug(
        title=f"{result.title} — {classification.replace('_', ' ')}",
        affected=result.file,
        classification=classification,
        confidence=confidence,
        steps=f"Run `{result.title}` in {result.file}",
        expected="test passes",
        actual=result.error or "test failed",
        reasoning=reasoning,
    )


def _extract_json(text: str) -> str:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text
