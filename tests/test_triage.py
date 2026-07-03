from anjalikastra.execution.runner import TestResult
from anjalikastra.llm.client import LLMClient
from anjalikastra.triage.classify_failures import triage_failure


async def test_triage_defaults_to_needs_human_review_when_uncertain():
    llm = LLMClient("cheap", "capable")  # no LLM configured in test env
    result = TestResult(file="about.spec.ts", title="renders heading", status="failed",
                         duration_ms=100, error="expected 'About' but got 'Home'")
    bug = await triage_failure(result, llm)
    assert bug.classification == "needs_human_review"
    assert bug.confidence < 0.5  # low confidence is surfaced, not hidden


async def test_triage_flags_timeouts_as_flake_with_low_confidence():
    llm = LLMClient("cheap", "capable")
    result = TestResult(file="products.spec.ts", title="loads", status="timedOut",
                         duration_ms=30000, error="Timeout 30000ms exceeded waiting for navigation")
    bug = await triage_failure(result, llm)
    assert bug.classification == "flake"
    assert bug.confidence < 0.5
