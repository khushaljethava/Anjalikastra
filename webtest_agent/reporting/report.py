"""Assemble the human-readable report.md and machine-readable report.json.

Every section that could imply completeness (coverage, pass rate) states its
denominator explicitly — this file is where the "coverage honesty is mandatory"
requirement actually gets enforced in the output.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from webtest_agent.cache.store import CacheStats
from webtest_agent.execution.runner import RunReport
from webtest_agent.generation.codegen import GeneratedFile
from webtest_agent.llm.client import TokenLedger
from webtest_agent.reporting.coverage import CoverageSummary
from webtest_agent.triage.classify_failures import DraftBug


@dataclass
class ReportData:
    url: str
    run_id: str
    generated_at: str
    coverage: CoverageSummary
    run_report: RunReport | None
    draft_bugs: list[DraftBug]
    generated_files: list[GeneratedFile]
    ledger: TokenLedger
    cache_stats: CacheStats
    suite_dir: str
    llm_provider: str | None = None  # None = heuristic-only run
    notes: list[str] = field(default_factory=list)


def build_report_data(**kwargs) -> ReportData:
    return ReportData(generated_at=datetime.datetime.utcnow().isoformat() + "Z", **kwargs)


def write_reports(data: ReportData, run_dir: Path) -> tuple[Path, Path]:
    md_path = run_dir / "report.md"
    json_path = run_dir / "report.json"
    md_path.write_text(_render_markdown(data))
    json_path.write_text(json.dumps(_to_json(data), indent=2, default=str))
    return md_path, json_path


def _to_json(data: ReportData) -> dict:
    return {
        "url": data.url,
        "run_id": data.run_id,
        "generated_at": data.generated_at,
        "coverage": {
            "known_pages": data.coverage.known_pages,
            "tested_pages": data.coverage.tested_pages,
            "coverage_percent": data.coverage.coverage_percent,
            "truncated": data.coverage.truncated,
            "public_only": data.coverage.public_only,
            "unreached": [asdict(u) for u in data.coverage.unreached],
        },
        "test_results": {
            "passed": data.run_report.passed if data.run_report else None,
            "failed": data.run_report.failed if data.run_report else None,
            "skipped": data.run_report.skipped if data.run_report else None,
            "results": [asdict(r) for r in data.run_report.results] if data.run_report else [],
        },
        "draft_bugs": [asdict(b) for b in data.draft_bugs],
        "suite": {
            "dir": data.suite_dir,
            "files": [
                {"path": f.relative_path, "source": f.source, "lines": f.review.line_count}
                for f in data.generated_files
            ],
        },
        "cost": {
            "llm_provider": data.llm_provider,
            "cheap_model_calls": data.ledger.cheap.calls,
            "capable_model_calls": data.ledger.capable.calls,
            "cheap_tokens": {"input": data.ledger.cheap.input_tokens, "output": data.ledger.cheap.output_tokens},
            "capable_tokens": {"input": data.ledger.capable.input_tokens, "output": data.ledger.capable.output_tokens},
            "cache_hit_rate": f"{data.cache_stats.hits}/{data.cache_stats.hits + data.cache_stats.misses}",
        },
        "notes": data.notes,
    }


def _render_markdown(data: ReportData) -> str:
    cov = data.coverage
    lines: list[str] = []
    lines.append(f"# webtest-agent report — {data.url}")
    lines.append("")
    lines.append(f"Generated: {data.generated_at}  \nRun ID: `{data.run_id}`")
    lines.append("")

    lines.append("## Coverage")
    lines.append("")
    lines.append(f"**Tested {cov.tested_pages} of {cov.known_pages} known pages ({cov.coverage_percent}%).**")
    if cov.public_only:
        lines.append("")
        lines.append("v1 scope: public pages only. Auth-gated areas are not covered by this run — see Phase 8/v2 for login support.")
    if cov.truncated:
        lines.append("")
        lines.append("Crawl was truncated at `--max-pages`; more pages likely exist and were not visited.")
    if cov.unreached:
        lines.append("")
        lines.append("### Not reached")
        lines.append("")
        lines.append("| URL | Reason |")
        lines.append("|---|---|")
        for u in cov.unreached[:200]:
            lines.append(f"| {u.url} | {u.reason} |")
    lines.append("")

    lines.append("## Test results")
    lines.append("")
    if data.run_report is None:
        lines.append("_Suite was not executed this run (dry-run, or execution was skipped)._")
    else:
        rr = data.run_report
        total = rr.passed + rr.failed + rr.skipped
        lines.append(f"**{rr.passed} passed, {rr.failed} failed, {rr.skipped} skipped** (of {total} tests).")
        failures = [r for r in rr.results if r.status in ("failed", "timedOut")]
        if failures:
            lines.append("")
            lines.append("| Test | File | Status | Error |")
            lines.append("|---|---|---|---|")
            for r in failures:
                err = (r.error or "").replace("\n", " ")[:120]
                lines.append(f"| {r.title} | {r.file} | {r.status} | {err} |")
    lines.append("")

    lines.append("## Drafted bugs (queued for human review — nothing here is auto-filed)")
    lines.append("")
    if not data.draft_bugs:
        lines.append("_None._")
    else:
        for b in data.draft_bugs:
            lines.append(f"### {b.title}")
            lines.append(f"- **Affected:** {b.affected}")
            lines.append(f"- **Classification:** {b.classification} (confidence {b.confidence:.2f})")
            lines.append(f"- **Steps:** {b.steps}")
            lines.append(f"- **Expected:** {b.expected}")
            lines.append(f"- **Actual:** {b.actual}")
            if b.reasoning:
                lines.append(f"- **Reasoning:** {b.reasoning}")
            lines.append("")

    lines.append("## Generated suite")
    lines.append("")
    lines.append(f"Location: `{data.suite_dir}`")
    lines.append("")
    lines.append("| File | Source | Lines |")
    lines.append("|---|---|---|")
    for f in data.generated_files:
        lines.append(f"| {f.relative_path} | {f.source} | {f.review.line_count} |")
    lines.append("")
    lines.append("Run it with:")
    lines.append("```bash")
    lines.append(f"cd {data.suite_dir}")
    lines.append("npm install && npx playwright install --with-deps chromium && npm test")
    lines.append("```")
    lines.append("")

    lines.append("## Cost")
    lines.append("")
    lines.append(f"- LLM provider: {data.llm_provider or 'none (heuristic/template-only run)'}")
    lines.append(f"- Cheap model: {data.ledger.cheap}")
    lines.append(f"- Capable model: {data.ledger.capable}")
    lines.append(f"- Content cache: {data.cache_stats}")
    lines.append("")

    if data.notes:
        lines.append("## Notes")
        lines.append("")
        for note in data.notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)
