"""Run the generated suite via Playwright CLI and parse results.

Shells out to `npm install` and `npx playwright test --reporter=json` rather than
reimplementing a test runner — the generated suite is a normal Playwright project,
so the normal Playwright CLI is the correct tool for running it (ladder rule #4).
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("webtest_agent.execution.runner")


class RunnerError(RuntimeError):
    pass


@dataclass
class TestResult:
    __test__ = False  # not a pytest test case; this is a Playwright test-case result

    file: str
    title: str
    status: str  # "passed" | "failed" | "timedOut" | "skipped"
    duration_ms: float
    error: str | None = None


@dataclass
class RunReport:
    results: list[TestResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == "passed")

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status in ("failed", "timedOut"))

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.status == "skipped")


async def _run(cmd: list[str], cwd: Path, timeout_s: float) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=str(cwd), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except asyncio.TimeoutError as exc:
        proc.kill()
        raise RunnerError(f"command timed out after {timeout_s}s: {' '.join(cmd)}") from exc
    return proc.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")


async def install_suite(suite_dir: Path, timeout_s: float = 300) -> None:
    logger.info("installing suite dependencies in %s", suite_dir)
    code, out, err = await _run(["npm", "install"], suite_dir, timeout_s)
    if code != 0:
        raise RunnerError(f"npm install failed (exit {code}):\n{err or out}")

    code, out, err = await _run(["npx", "playwright", "install", "--with-deps", "chromium"], suite_dir, timeout_s)
    if code != 0:
        raise RunnerError(f"playwright browser install failed (exit {code}):\n{err or out}")


async def run_suite(suite_dir: Path, timeout_s: float = 300) -> RunReport:
    report_path = suite_dir / "results.json"
    cmd = ["npx", "playwright", "test", "--reporter=json"]
    code, out, err = await _run(cmd, suite_dir, timeout_s)

    try:
        payload = json.loads(out)
    except json.JSONDecodeError as exc:
        raise RunnerError(f"could not parse playwright JSON reporter output (exit {code}):\n{err[:2000]}") from exc

    report_path.write_text(json.dumps(payload, indent=2))
    return _parse_report(payload)


def _parse_report(payload: dict) -> RunReport:
    results: list[TestResult] = []

    def walk(suite: dict, file_hint: str = "") -> None:
        file_name = suite.get("file", file_hint)
        for spec in suite.get("specs", []):
            for test in spec.get("tests", []):
                for result in test.get("results", []):
                    results.append(
                        TestResult(
                            file=file_name,
                            title=spec.get("title", "unknown"),
                            status=result.get("status", "unknown"),
                            duration_ms=result.get("duration", 0),
                            error=(result.get("error") or {}).get("message"),
                        )
                    )
        for child in suite.get("suites", []):
            walk(child, file_name)

    for top_suite in payload.get("suites", []):
        walk(top_suite)

    return RunReport(results=results)
