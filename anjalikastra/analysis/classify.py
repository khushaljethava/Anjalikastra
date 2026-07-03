"""Page-type and endpoint-type classification (cheap model, cached by content-hash).

Classification drives which assertions get generated later — a checkout page and a
blog post need very different checks, so getting the type label right (or at least
flagging low confidence honestly) matters more than raw crawl speed.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from anjalikastra.cache.store import CacheStore, content_hash
from anjalikastra.discovery.crawler import PageRecord
from anjalikastra.discovery.endpoints import EndpointRecord
from anjalikastra.llm.client import LLMClient, LLMUnavailable

logger = logging.getLogger("anjalikastra.analysis.classify")

PAGE_TYPES = [
    "home", "login", "signup", "listing", "detail", "checkout", "form",
    "article", "dashboard", "search", "error", "static", "other",
]
ENDPOINT_TYPES = ["read_list", "read_detail", "mutation", "auth", "health", "other"]

_LOW_CONFIDENCE = 0.4


@dataclass
class PageClassification:
    url: str
    page_type: str
    confidence: float
    reasoning: str = ""


@dataclass
class EndpointClassification:
    method: str
    path_pattern: str
    endpoint_type: str
    confidence: float
    reasoning: str = ""


def _heuristic_page_type(url: str, html: str) -> tuple[str, float]:
    path = url.lower()
    lower_html = html.lower()
    checks: list[tuple[str, float, bool]] = [
        ("login", 0.7, any(k in path for k in ("/login", "/signin", "/sign-in"))
         or ('type="password"' in lower_html and "login" in lower_html)),
        ("signup", 0.7, any(k in path for k in ("/signup", "/register", "/sign-up"))),
        ("checkout", 0.7, any(k in path for k in ("/checkout", "/cart", "/payment"))),
        ("search", 0.6, "/search" in path or 'type="search"' in lower_html),
        ("dashboard", 0.5, any(k in path for k in ("/dashboard", "/account", "/admin"))),
        ("error", 0.6, any(k in path for k in ("/404", "/error", "/not-found"))),
        ("article", 0.5, any(k in path for k in ("/blog", "/post", "/article", "/news"))),
        ("listing", 0.4, "<ul" in lower_html and lower_html.count("<li") > 8),
        ("form", 0.4, lower_html.count("<form") >= 1),
    ]
    for label, confidence, matched in checks:
        if matched:
            return label, confidence
    if path.rstrip("/").split("/")[-1] in ("", url):
        return "home", 0.3
    return "other", 0.2


def _heuristic_endpoint_type(method: str, path_pattern: str) -> tuple[str, float]:
    p = path_pattern.lower()
    if any(k in p for k in ("/auth", "/login", "/token", "/session")):
        return "auth", 0.6
    if any(k in p for k in ("/health", "/status", "/ping")):
        return "health", 0.7
    if method == "GET":
        return ("read_detail" if ":id" in p else "read_list"), 0.5
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        return "mutation", 0.6
    return "other", 0.2


async def classify_page(page: PageRecord, html: str, llm: LLMClient, cache: CacheStore) -> PageClassification:
    h = content_hash(html or page.url)
    cached = cache.get("page_classification", page.url, h)
    if cached:
        return PageClassification(**cached)

    heuristic_type, heuristic_conf = _heuristic_page_type(page.url, html)
    result = PageClassification(url=page.url, page_type=heuristic_type, confidence=heuristic_conf,
                                 reasoning="heuristic (no LLM configured)")

    if llm.available:
        try:
            snippet = re.sub(r"\s+", " ", html)[:3000]
            prompt = (
                f"Classify this web page's type. URL: {page.url}\n"
                f"Allowed types: {', '.join(PAGE_TYPES)}\n"
                f"HTML excerpt: {snippet}\n\n"
                'Reply with strict JSON: {"page_type": "...", "confidence": 0.0-1.0, "reasoning": "one sentence"}'
            )
            raw = await llm.acomplete(
                "cheap", system="You are a precise web page classifier. Reply with JSON only.",
                prompt=prompt, max_tokens=200,
            )
            parsed = json.loads(_extract_json(raw))
            page_type = parsed.get("page_type") if parsed.get("page_type") in PAGE_TYPES else "other"
            result = PageClassification(
                url=page.url,
                page_type=page_type,
                confidence=float(parsed.get("confidence", 0.5)),
                reasoning=parsed.get("reasoning", ""),
            )
        except (LLMUnavailable, json.JSONDecodeError, ValueError, KeyError) as exc:
            logger.debug("page classification LLM call failed for %s, using heuristic: %s", page.url, exc)

    if result.confidence < _LOW_CONFIDENCE:
        logger.info("low-confidence classification for %s: %s (%.2f)", page.url, result.page_type, result.confidence)

    cache.set("page_classification", page.url, h, result.__dict__)
    return result


async def classify_endpoint(endpoint: EndpointRecord, llm: LLMClient, cache: CacheStore) -> EndpointClassification:
    key = f"{endpoint.method} {endpoint.path_pattern}"
    h = content_hash(key + (endpoint.sample_response_body or ""))
    cached = cache.get("endpoint_classification", key, h)
    if cached:
        return EndpointClassification(**cached)

    heuristic_type, heuristic_conf = _heuristic_endpoint_type(endpoint.method, endpoint.path_pattern)
    result = EndpointClassification(method=endpoint.method, path_pattern=endpoint.path_pattern,
                                     endpoint_type=heuristic_type, confidence=heuristic_conf,
                                     reasoning="heuristic (no LLM configured)")

    if llm.available:
        try:
            prompt = (
                f"Classify this API endpoint's type.\n"
                f"Method: {endpoint.method}\nPath pattern: {endpoint.path_pattern}\n"
                f"Allowed types: {', '.join(ENDPOINT_TYPES)}\n"
                f"Sample response (may be empty): {(endpoint.sample_response_body or '')[:800]}\n\n"
                'Reply with strict JSON: {"endpoint_type": "...", "confidence": 0.0-1.0, "reasoning": "one sentence"}'
            )
            raw = await llm.acomplete(
                "cheap", system="You are a precise API endpoint classifier. Reply with JSON only.",
                prompt=prompt, max_tokens=200,
            )
            parsed = json.loads(_extract_json(raw))
            endpoint_type = parsed.get("endpoint_type") if parsed.get("endpoint_type") in ENDPOINT_TYPES else "other"
            result = EndpointClassification(
                method=endpoint.method,
                path_pattern=endpoint.path_pattern,
                endpoint_type=endpoint_type,
                confidence=float(parsed.get("confidence", 0.5)),
                reasoning=parsed.get("reasoning", ""),
            )
        except (LLMUnavailable, json.JSONDecodeError, ValueError, KeyError) as exc:
            logger.debug("endpoint classification LLM call failed for %s, using heuristic: %s", key, exc)

    cache.set("endpoint_classification", key, h, result.__dict__)
    return result


def _extract_json(text: str) -> str:
    """Models sometimes wrap JSON in prose or code fences; pull out the {...} block."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text
