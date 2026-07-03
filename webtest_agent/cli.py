"""`webtest-agent <url> [flags]` — entrypoint."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from webtest_agent.config import Config
from webtest_agent.orchestrator import run_pipeline

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()


@app.command()
def main(
    url: str = typer.Argument(..., help="Target site URL, e.g. https://example.com"),
    output_dir: Path = typer.Option(Path("output"), "--output-dir", help="Where run artifacts are written."),
    max_pages: int = typer.Option(40, "--max-pages", help="Cap on pages crawled."),
    throttle_ms: int = typer.Option(500, "--throttle-ms", help="Minimum delay between requests, in ms."),
    openapi: Optional[Path] = typer.Option(None, "--openapi", help="Optional OpenAPI spec to enrich endpoint discovery."),
    public_only: bool = typer.Option(True, "--public-only/--allow-auth", help="v1: only crawl unauthenticated, public pages."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the plan and exit without making network requests."),
    resume: Optional[str] = typer.Option(
        None, "--resume", help="Resume a previous run by its run-id (reuses output/<run-id>), skipping discovery if it already completed."
    ),
    cheap_model: Optional[str] = typer.Option(
        None, "--cheap-model", help="Model for classification/summaries (default: env WEBTEST_AGENT_CHEAP_MODEL or claude-haiku-4-5-20251001)."
    ),
    capable_model: Optional[str] = typer.Option(
        None, "--capable-model", help="Model for test generation/triage (default: env WEBTEST_AGENT_CAPABLE_MODEL or claude-sonnet-5)."
    ),
    llm_provider: Optional[str] = typer.Option(
        None, "--llm-provider",
        help="LLM backend: 'anthropic' or 'openai' (any OpenAI-compatible endpoint: OpenAI, Ollama, OpenRouter, Gemini, ...). "
        "Default: env WEBTEST_AGENT_LLM_PROVIDER, else auto-detected from which API keys are set.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging."),
) -> None:
    """Crawl URL, generate a runnable E2E/functional Playwright suite, and produce a report."""
    if not url.startswith(("http://", "https://")):
        console.print(f"[red]error:[/red] URL must start with http:// or https:// (got: {url!r})")
        raise typer.Exit(code=2)
    if max_pages < 1:
        console.print(f"[red]error:[/red] --max-pages must be at least 1 (got: {max_pages})")
        raise typer.Exit(code=2)
    if throttle_ms < 0:
        console.print(f"[red]error:[/red] --throttle-ms cannot be negative (got: {throttle_ms})")
        raise typer.Exit(code=2)
    if openapi is not None and not openapi.exists():
        console.print(f"[red]error:[/red] --openapi path does not exist: {openapi}")
        raise typer.Exit(code=2)

    overrides = {}
    if cheap_model:
        overrides["cheap_model"] = cheap_model
    if capable_model:
        overrides["capable_model"] = capable_model
    if llm_provider:
        overrides["llm_provider"] = llm_provider

    cfg = Config(
        url=url,
        output_dir=output_dir,
        run_id=resume,
        max_pages=max_pages,
        throttle_ms=throttle_ms,
        openapi_path=openapi,
        public_only=public_only,
        dry_run=dry_run,
        verbose=verbose,
        **overrides,
    )

    try:
        provider = cfg.resolved_llm_provider
    except ValueError as exc:
        console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(code=2)

    if dry_run:
        _print_plan(cfg, provider)
        raise typer.Exit(code=0)

    if provider is None:
        console.print(
            "[yellow]warning:[/yellow] no LLM backend configured. "
            "Classification and generation will fall back to heuristic-only mode, "
            "which produces a smaller, less targeted suite. Set ANTHROPIC_API_KEY, "
            "or OPENAI_API_KEY / OPENAI_BASE_URL for an OpenAI-compatible endpoint "
            "(OpenAI, Ollama, OpenRouter, Gemini, ...)."
        )
    elif provider != "anthropic" and cfg.capable_model.startswith("claude-"):
        console.print(
            f"[yellow]warning:[/yellow] provider is '{provider}' but the models are still the Claude "
            "defaults. Pass --cheap-model/--capable-model with names your endpoint serves."
        )

    try:
        exit_code = asyncio.run(run_pipeline(cfg, console=console))
    except KeyboardInterrupt:
        console.print("\n[yellow]interrupted[/yellow] — partial run state is saved under " + str(cfg.run_dir))
        raise typer.Exit(code=130)
    raise typer.Exit(code=exit_code)


def _print_plan(cfg: Config, provider: str | None) -> None:
    table = Table(title=f"webtest-agent plan for {cfg.url}", show_header=False)
    table.add_row("run id", cfg.run_id)
    table.add_row("output dir", str(cfg.run_dir))
    table.add_row("max pages", str(cfg.max_pages))
    table.add_row("throttle", f"{cfg.throttle_ms}ms between requests")
    table.add_row("robots.txt", "respected" if cfg.respect_robots else "ignored")
    table.add_row("scope", "public pages only (v1)" if cfg.public_only else "auth-aware (v2, if configured)")
    table.add_row("openapi enrichment", str(cfg.openapi_path) if cfg.openapi_path else "none")
    table.add_row("llm provider", provider or "none (heuristic fallback)")
    if provider == "openai":
        import os

        table.add_row("llm base url", os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1 (default)")
    table.add_row("cheap model", cfg.cheap_model)
    table.add_row("capable model", cfg.capable_model)
    console.print(table)

    console.print("\n[bold]Steps this run would take:[/bold]")
    steps = [
        "1. Discovery: fetch sitemap.xml (seed list) + BFS crawl same-origin pages, respecting robots.txt and throttle.",
        "2. Discovery: capture XHR/fetch traffic per page to build the endpoint surface"
        + (f" (merged with {cfg.openapi_path})" if cfg.openapi_path else ""),
        "3. Analysis: classify each page/endpoint by type (cheap model, cached by content-hash).",
        "4. Generation: infer assertions and emit Playwright .spec.ts files, config, package.json, README.",
        "5. Generation: run every emitted file through the minimal-code review gate.",
        "6. Execution: install deps, run the suite, capture baseline DOM/screenshots.",
        "7. Triage: classify failures (regression/flake/expected-change/needs-human-review), draft bug reports.",
        "8. Reporting: write report.md + report.json with honest coverage accounting.",
    ]
    for step in steps:
        console.print(f"  {step}")
    console.print(f"\nOutputs would be written under: [bold]{cfg.run_dir}[/bold]")


if __name__ == "__main__":
    app()
