"""Wires the phases together: discovery -> analysis -> generation -> execution -> triage -> reporting.

Kept as one module (not split further) because it's a linear pipeline with no
reusable pieces of its own — everything reusable already lives in the phase
modules it calls.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import httpx
from playwright.async_api import async_playwright
from rich.console import Console

from anjalikastra.analysis.classify import classify_endpoint, classify_page
from anjalikastra.cache.store import CacheStore
from anjalikastra.checkpoint import Checkpoint
from anjalikastra.config import Config
from anjalikastra.discovery.crawler import CrawlResult, Throttle, crawl
from anjalikastra.discovery.endpoints import (
    EndpointRecord,
    capture_endpoints_for_pages,
    load_openapi_endpoints,
    merge_endpoints,
)
from anjalikastra.discovery.sitemap import fetch_sitemap_urls
from anjalikastra.execution.baseline import BaselineStore
from anjalikastra.execution.runner import RunnerError, install_suite, run_suite
from anjalikastra.generation.assertions import PageAssertions, infer_endpoint_assertions, infer_page_assertions
from anjalikastra.generation.codegen import GeneratedFile, generate_endpoint_files, generate_page_files
from anjalikastra.generation.templates.scaffold import render_package_json, render_playwright_config, render_readme
from anjalikastra.llm.client import LLMClient, TokenLedger
from anjalikastra.reporting.coverage import CoverageSummary, build_coverage
from anjalikastra.reporting.report import build_report_data, write_reports
from anjalikastra.triage.classify_failures import DraftBug, triage_failure

logger = logging.getLogger("anjalikastra.orchestrator")


def _write_suite(cfg: Config, generated_files: list[GeneratedFile]) -> None:
    import datetime

    (cfg.suite_dir / "tests" / "pages").mkdir(parents=True, exist_ok=True)
    (cfg.suite_dir / "tests" / "api").mkdir(parents=True, exist_ok=True)

    (cfg.suite_dir / "package.json").write_text(render_package_json(cfg.url))
    (cfg.suite_dir / "playwright.config.ts").write_text(render_playwright_config(cfg.url))
    (cfg.suite_dir / "README.md").write_text(
        render_readme(cfg.url, datetime.datetime.utcnow().strftime("%Y-%m-%d"))
    )

    for gf in generated_files:
        path = cfg.suite_dir / gf.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(gf.content)


async def _discover(cfg: Config, console: Console, checkpoint: Checkpoint) -> tuple[CrawlResult, list[EndpointRecord]]:
    """Crawl + endpoint capture, checkpointed: a crash after this point resumes
    without hitting the target site again."""
    cached = checkpoint.get("discovery")
    if cached:
        console.print("[dim]Resuming: reusing checkpointed discovery results.[/dim]")
        crawl_result = CrawlResult.from_dict(cached["crawl"])
        endpoints = [EndpointRecord.from_dict(e) for e in cached["endpoints"]]
        return crawl_result, endpoints

    console.print(f"[bold]Discovering[/bold] {cfg.url} ...")
    headers = {"User-Agent": cfg.user_agent}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        seeds = await fetch_sitemap_urls(cfg.url, client)
        crawl_result = await crawl(cfg.url, seeds, cfg.max_pages, cfg.throttle_ms, cfg.respect_robots, client)

    reachable = [p for p in crawl_result.pages if p.status and p.status < 400]
    console.print(f"  {len(crawl_result.pages)} pages visited, {len(reachable)} reachable (2xx/3xx).")

    console.print("[bold]Capturing API traffic[/bold] ...")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(executable_path=cfg.chromium_executable_path)
        try:
            html_page_urls = [p.url for p in reachable if p.url in crawl_result.html_by_url]
            throttle = Throttle(cfg.throttle_ms)
            observed_endpoints = await capture_endpoints_for_pages(browser, html_page_urls, throttle)
        finally:
            await browser.close()

    documented_endpoints = []
    if cfg.openapi_path:
        documented_endpoints = load_openapi_endpoints(Path(cfg.openapi_path))
    endpoints = merge_endpoints(observed_endpoints, documented_endpoints)
    console.print(f"  {len(endpoints)} distinct endpoints discovered.")

    checkpoint.save("discovery", {"crawl": crawl_result.to_dict(), "endpoints": [e.to_dict() for e in endpoints]})
    return crawl_result, endpoints


async def _classify_and_infer(
    cfg: Config, crawl_result: CrawlResult, endpoints: list[EndpointRecord], llm: LLMClient, cache: CacheStore
) -> tuple[list[PageAssertions], list, dict[str, str]]:
    """Classification is cheap-model work independent of the target site's throttle,
    so it's run with bounded concurrency rather than one call at a time."""
    reachable = [p for p in crawl_result.pages if p.status and p.status < 400 and p.url in crawl_result.html_by_url]
    semaphore = asyncio.Semaphore(cfg.classification_concurrency)

    async def classify_one_page(page):
        html = crawl_result.html_by_url[page.url]
        async with semaphore:
            classification = await classify_page(page, html, llm, cache)
        return infer_page_assertions(page, html, classification, cfg.load_time_threshold_ms)

    page_assertions_list = list(await asyncio.gather(*(classify_one_page(p) for p in reachable)))

    async def classify_one_endpoint(ep: EndpointRecord):
        async with semaphore:
            classification = await classify_endpoint(ep, llm, cache)
        return infer_endpoint_assertions(ep, classification)

    endpoint_assertions_list = list(await asyncio.gather(*(classify_one_endpoint(e) for e in endpoints)))
    sample_urls = {
        f"{ep.method} {ep.path_pattern}": (ep.observed_urls[0] if ep.observed_urls else ep.path_pattern)
        for ep in endpoints
    }
    return page_assertions_list, endpoint_assertions_list, sample_urls


async def _capture_baselines(cfg: Config, page_assertions_list: list[PageAssertions]) -> list:
    baseline_store = BaselineStore(cfg.output_dir / ".baseline")
    diffs = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(executable_path=cfg.chromium_executable_path)
        try:
            page = await browser.new_page()
            for a in page_assertions_list:
                try:
                    await page.goto(a.url, timeout=cfg.playwright_timeout_ms)
                    baseline = await baseline_store.capture(page, a.url)
                    diffs.append(baseline_store.diff_and_store(baseline))
                except Exception as exc:  # noqa: BLE001 - baseline capture is best-effort, never fatal
                    logger.debug("baseline capture failed for %s: %s", a.url, exc)
            await page.close()
        finally:
            await browser.close()
    return diffs


def _diffs_to_draft_bugs(diffs: list) -> list[DraftBug]:
    return [
        DraftBug(
            title=f"Structural change detected on {d.url}",
            affected=d.url,
            classification="needs_human_review",
            confidence=0.5,
            steps=f"Diff current DOM structure of {d.url} against the stored baseline.",
            expected=f"structure hash {d.previous_hash}",
            actual=f"structure hash {d.current_hash}",
            reasoning="DOM structure changed since the last recorded baseline.",
        )
        for d in diffs
        if d.changed
    ]


async def run_pipeline(cfg: Config, console: Console) -> int:
    logging.basicConfig(
        level=logging.DEBUG if cfg.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    cfg.run_dir.mkdir(parents=True, exist_ok=True)
    notes: list[str] = []

    ledger = TokenLedger()
    llm = LLMClient(cfg.cheap_model, cfg.capable_model, ledger, provider=cfg.llm_provider)
    cache = CacheStore(cfg.cache_dir)
    checkpoint = Checkpoint(cfg.run_dir)

    generated_files: list[GeneratedFile] = []
    coverage = CoverageSummary(known_pages=0, tested_pages=0)
    run_report = None
    draft_bugs: list[DraftBug] = []

    try:
        crawl_result, endpoints = await _discover(cfg, console, checkpoint)
        reachable = [p for p in crawl_result.pages if p.status and p.status < 400]

        if not reachable:
            console.print(
                "[red]The crawler could not reach any pages.[/red] This often means the site's bot "
                "protection is blocking the crawler. Anjalikastra does not attempt to evade bot "
                f"detection — instead, allowlist this tool's User-Agent on your own site:\n"
                f"  [bold]{cfg.user_agent}[/bold]"
            )
            notes.append("Crawl reached zero pages; the target may be blocking the crawler's User-Agent.")

        console.print("[bold]Classifying[/bold] pages and endpoints ...")
        page_assertions_list, endpoint_assertions_list, sample_urls = await _classify_and_infer(
            cfg, crawl_result, endpoints, llm, cache
        )
        tested_urls = {a.url for a in page_assertions_list}

        console.print("[bold]Generating[/bold] Playwright test files ...")
        generated_files = list(await generate_page_files(page_assertions_list, llm, cfg.classification_concurrency))
        generated_files.extend(
            await generate_endpoint_files(endpoint_assertions_list, sample_urls, llm, cfg.classification_concurrency)
        )

        rejected = [gf for gf in generated_files if not gf.review.passed]
        if rejected:
            notes.append(f"{len(rejected)} generated file(s) still had review-gate violations after fallback.")

        _write_suite(cfg, generated_files)
        console.print(f"  {len(generated_files)} test files written to {cfg.suite_dir}")

        diffs = await _capture_baselines(cfg, page_assertions_list)
        draft_bugs.extend(_diffs_to_draft_bugs(diffs))

        if not cfg.dry_run and generated_files:
            console.print("[bold]Running[/bold] the generated suite ...")
            try:
                await install_suite(cfg.suite_dir)
                run_report = await run_suite(cfg.suite_dir)
                console.print(f"  {run_report.passed} passed, {run_report.failed} failed, {run_report.skipped} skipped")
            except RunnerError as exc:
                console.print(f"[yellow]warning:[/yellow] could not execute the generated suite: {exc}")
                notes.append(f"Suite execution failed: {exc}")

        if run_report:
            for r in run_report.results:
                if r.status in ("failed", "timedOut"):
                    draft_bugs.append(await triage_failure(r, llm))

        coverage = build_coverage(crawl_result, tested_urls, cfg.public_only)

    except Exception as exc:  # noqa: BLE001 - a crash still gets a partial report + resumable checkpoint, not silence
        logger.exception("pipeline failed")
        notes.append(f"Run failed before completing: {exc}. Resume with `--resume {cfg.run_id}`.")
        console.print(f"[red]error:[/red] {exc}")
        console.print(f"Partial state saved. Resume with: Anjalikastra {cfg.url} --resume {cfg.run_id}")

    cache.flush()
    report_data = build_report_data(
        url=cfg.url,
        run_id=cfg.run_id,
        coverage=coverage,
        run_report=run_report,
        draft_bugs=draft_bugs,
        generated_files=generated_files,
        ledger=ledger,
        cache_stats=cache.stats,
        suite_dir=str(cfg.suite_dir),
        llm_provider=llm.provider,
        notes=notes,
    )
    md_path, _json_path = write_reports(report_data, cfg.run_dir)

    console.print(f"\n[bold]Report:[/bold] {md_path}")
    console.print(f"Coverage: {coverage.tested_pages}/{coverage.known_pages} pages ({coverage.coverage_percent}%)")
    console.print(f"Tokens: {ledger.summary()}")

    if coverage.tested_pages == 0:
        return 1
    if run_report and run_report.failed > 0:
        return 1
    if any("Run failed before completing" in n for n in notes):
        return 1
    return 0
