"""Emit idiomatic Playwright Test (.spec.ts) files.

Generation is a hybrid: a deterministic template always produces a valid, working
draft from the inferred assertions (assertions.py) — this is what guarantees the
suite installs and runs on first try even with no LLM configured. When a capable
model is available, it's given that draft and asked to improve it into more
idiomatic/thorough test code; the result only ships if it survives review_gate,
otherwise the deterministic draft ships instead. Either way, output always passes
the review gate — nothing bypasses it.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from urllib.parse import urlparse

from webtest_agent.generation.assertions import EndpointAssertions, PageAssertions, slugify
from webtest_agent.generation.review_gate import ReviewResult, review_file
from webtest_agent.llm.client import LLMClient, LLMUnavailable

logger = logging.getLogger("webtest_agent.generation.codegen")


@dataclass
class GeneratedFile:
    relative_path: str
    content: str
    review: ReviewResult
    source: str  # "llm" or "deterministic"


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


def _page_describe_name(assertions: PageAssertions) -> str:
    path = urlparse(assertions.url).path or "/"
    return f"{assertions.page_type}: {path}"


def generate_page_spec_deterministic(assertions: PageAssertions) -> str:
    lines: list[str] = []
    lines.append("import { test, expect } from '@playwright/test';")
    lines.append("")
    lines.append(f"test.describe('{_esc(_page_describe_name(assertions))}', () => {{")
    lines.append(f"  test('loads with a healthy status', async ({{ page }}) => {{")
    lines.append(f"    const response = await page.goto('{_esc(assertions.url)}');")
    if assertions.expected_status_ok:
        lines.append("    expect(response?.status()).toBeLessThan(400);")
    else:
        lines.append("    expect(response?.status()).toBeGreaterThanOrEqual(400);")
    lines.append("  });")
    lines.append("")

    if assertions.title:
        lines.append("  test('has the expected title', async ({ page }) => {")
        lines.append(f"    await page.goto('{_esc(assertions.url)}');")
        lines.append(f"    await expect(page).toHaveTitle('{_esc(assertions.title)}');")
        lines.append("  });")
        lines.append("")

    if assertions.h1_text:
        lines.append("  test('renders the main heading', async ({ page }) => {")
        lines.append(f"    await page.goto('{_esc(assertions.url)}');")
        lines.append(f"    await expect(page.locator('h1').first()).toContainText('{_esc(assertions.h1_text[:80])}');")
        lines.append("  });")
        lines.append("")

    if assertions.has_nav:
        lines.append("  test('renders primary navigation', async ({ page }) => {")
        lines.append(f"    await page.goto('{_esc(assertions.url)}');")
        lines.append("    await expect(page.locator('nav').first()).toBeVisible();")
        lines.append("  });")
        lines.append("")

    lines.append(f"  test('loads within {assertions.load_time_threshold_ms}ms', async ({{ page }}) => {{")
    lines.append("    const start = Date.now();")
    lines.append(f"    await page.goto('{_esc(assertions.url)}', {{ waitUntil: 'load' }});")
    lines.append(f"    expect(Date.now() - start).toBeLessThan({assertions.load_time_threshold_ms});")
    lines.append("  });")
    lines.append("")

    lines.append("  test('has no unhandled console errors', async ({ page }) => {")
    lines.append("    const errors: string[] = [];")
    lines.append("    page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });")
    lines.append(f"    await page.goto('{_esc(assertions.url)}');")
    lines.append("    expect(errors).toEqual([]);")
    lines.append("  });")

    for i, form in enumerate(assertions.forms):
        if not form.required_fields:
            continue
        lines.append("")
        lines.append(f"  test('form #{i + 1} marks its required fields', async ({{ page }}) => {{")
        lines.append(f"    await page.goto('{_esc(assertions.url)}');")
        lines.append(f"    const form = page.locator('form').nth({i});")
        for field_name in form.required_fields[:5]:
            lines.append(
                f"    await expect(form.locator('[name=\"{_esc(field_name)}\"], #{_esc(field_name)}').first()).toHaveAttribute('required', '');"
            )
        lines.append("  });")

    lines.append("});")
    lines.append("")
    return "\n".join(lines)


def generate_endpoint_spec_deterministic(assertions_list: list[EndpointAssertions], resource_path: str, sample_urls: dict[str, str]) -> str:
    lines: list[str] = []
    lines.append("import { test, expect } from '@playwright/test';")
    lines.append("")
    lines.append(f"test.describe('API resource: {_esc(resource_path)}', () => {{")

    for a in assertions_list:
        sample_url = sample_urls.get(f"{a.method} {a.path_pattern}", a.path_pattern)
        test_name = f"{a.method} {a.path_pattern} returns {a.expected_status}"
        lines.append(f"  test('{_esc(test_name)}', async ({{ request }}) => {{")
        method_call = a.method.lower()
        lines.append(f"    const res = await request.{method_call}('{_esc(sample_url)}');")
        lines.append(f"    expect(res.status()).toBe({a.expected_status});")
        if a.response_is_json:
            lines.append("    const body = await res.json();")
            for key in a.response_top_level_keys[:5]:
                lines.append(f"    expect(body).toHaveProperty('{_esc(key)}');")
        lines.append("  });")
        lines.append("")

        if "missing_auth" in a.negative_cases:
            lines.append(f"  test('{_esc(a.method + ' ' + a.path_pattern)} rejects unauthenticated requests', async ({{ request }}) => {{")
            lines.append(f"    const res = await request.{method_call}('{_esc(sample_url)}', {{ headers: {{ Authorization: '' }} }});")
            lines.append("    expect([401, 403]).toContain(res.status());")
            lines.append("  });")
            lines.append("")

        if "invalid_id" in a.negative_cases:
            invalid_url = sample_url.rsplit("/", 1)[0] + "/nonexistent-id-000000"
            lines.append(f"  test('{_esc(a.method + ' ' + a.path_pattern)} 404s on an unknown id', async ({{ request }}) => {{")
            lines.append(f"    const res = await request.{method_call}('{_esc(invalid_url)}');")
            lines.append("    expect([404, 400]).toContain(res.status());")
            lines.append("  });")
            lines.append("")

    lines.append("});")
    lines.append("")
    return "\n".join(lines)


async def _try_llm_enhance(draft: str, context: str, llm: LLMClient) -> str | None:
    if not llm.available:
        return None
    try:
        prompt = (
            "Improve this generated Playwright Test file into idiomatic, thorough, "
            "readable TypeScript. Keep every existing assertion's intent, but you may "
            "add more specific web-first assertions where the context supports it. "
            "Do NOT add page-object classes, custom wait helpers, or hand-rolled sleeps. "
            "Do NOT add explanatory comments describing what the code obviously does. "
            "Reply with ONLY the final .spec.ts file contents, no markdown fences, no prose.\n\n"
            f"Context:\n{context}\n\nDraft:\n{draft}"
        )
        result = await llm.acomplete(
            "capable",
            system="You are a senior test engineer writing idiomatic Playwright Test files.",
            prompt=prompt,
            max_tokens=2000,
        )
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
            cleaned = cleaned.rsplit("```", 1)[0]
        return cleaned.strip() + "\n"
    except LLMUnavailable:
        return None
    except Exception as exc:  # noqa: BLE001 - generation must never crash the run; fall back to the draft
        logger.warning("LLM enhancement failed, keeping deterministic draft: %s", exc)
        return None


async def generate_page_file(assertions: PageAssertions, llm: LLMClient) -> GeneratedFile:
    draft = generate_page_spec_deterministic(assertions)
    filename = f"tests/pages/{slugify(urlparse(assertions.url).path or 'home')}.spec.ts"

    content, source = draft, "deterministic"
    enhanced = await _try_llm_enhance(draft, f"Page type: {assertions.page_type}, URL: {assertions.url}", llm)
    if enhanced:
        review = review_file(enhanced, filename)
        if review.passed:
            content, source = enhanced, "llm"
        else:
            logger.info("review gate rejected LLM output for %s, using deterministic draft: %s", filename, review.violations)

    review = review_file(content, filename)
    if not review.passed and source == "llm":
        content, source = draft, "deterministic"
        review = review_file(content, filename)
    return GeneratedFile(relative_path=filename, content=content, review=review, source=source)


async def generate_page_files(
    assertions_list: list[PageAssertions], llm: LLMClient, concurrency: int = 5
) -> list[GeneratedFile]:
    """Generate one file per page, bounded-concurrent: LLM calls are independent of
    each other and of the target site's throttle, so there's no reason to serialize them."""
    semaphore = asyncio.Semaphore(concurrency)

    async def worker(assertions: PageAssertions) -> GeneratedFile:
        async with semaphore:
            return await generate_page_file(assertions, llm)

    return list(await asyncio.gather(*(worker(a) for a in assertions_list)))


async def generate_endpoint_file(
    group: list[EndpointAssertions], resource_path: str, sample_urls: dict[str, str], llm: LLMClient
) -> GeneratedFile:
    draft = generate_endpoint_spec_deterministic(group, resource_path, sample_urls)
    filename = f"tests/api/{slugify(resource_path)}.spec.ts"

    content, source = draft, "deterministic"
    context = f"API resource: {resource_path}, methods: {[a.method for a in group]}"
    enhanced = await _try_llm_enhance(draft, context, llm)
    if enhanced:
        review = review_file(enhanced, filename)
        if review.passed:
            content, source = enhanced, "llm"
        else:
            logger.info("review gate rejected LLM output for %s, using deterministic draft: %s", filename, review.violations)

    review = review_file(content, filename)
    if not review.passed and source == "llm":
        content, source = draft, "deterministic"
        review = review_file(content, filename)
    return GeneratedFile(relative_path=filename, content=content, review=review, source=source)


async def generate_endpoint_files(
    endpoint_assertions: list[EndpointAssertions], sample_urls: dict[str, str], llm: LLMClient, concurrency: int = 5
) -> list[GeneratedFile]:
    by_resource: dict[str, list[EndpointAssertions]] = {}
    for a in endpoint_assertions:
        by_resource.setdefault(a.path_pattern, []).append(a)

    semaphore = asyncio.Semaphore(concurrency)

    async def worker(resource_path: str, group: list[EndpointAssertions]) -> GeneratedFile:
        async with semaphore:
            return await generate_endpoint_file(group, resource_path, sample_urls, llm)

    return list(await asyncio.gather(*(worker(rp, g) for rp, g in by_resource.items())))
