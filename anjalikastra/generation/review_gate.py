"""Minimal-code ladder review, applied to every generated test file before it ships.

This is a product feature, not internal cleanup: users keep and maintain these
files, so bloat here is exactly the maintenance burden this tool exists to remove.
Checks are deliberately conservative (regex-based, not a TS parser) — false
negatives are fine, false positives that reject good idiomatic tests are not.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_MAX_LINES = 200

_FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    (r"\bwaitForTimeout\s*\(", "hand-rolled waitForTimeout(ms) sleep — use a web-first `expect(...).toBeVisible()`/auto-waiting locator instead"),
    (r"while\s*\(\s*true\s*\)", "manual polling loop — Playwright's auto-waiting or `expect.poll` replaces this"),
    (r"\bclass\s+\w*Page\w*\s*\{", "page-object class for what looks like a single-use test file — inline the locators instead"),
    (r"function\s+customExpect|function\s+assertThat|function\s+myAssert", "hand-rolled assertion wrapper — use Playwright's built-in `expect`"),
    (r"\bsetTimeout\s*\(", "raw setTimeout — use Playwright's auto-waiting instead of manual delays"),
]

_REQUIRED_PATTERNS: list[tuple[str, str]] = [
    (r"from ['\"]@playwright/test['\"]", "must import from '@playwright/test'"),
    (r"\btest\s*\(", "must contain at least one test() case"),
    (r"\bexpect\s*\(", "must contain at least one expect() assertion"),
]


@dataclass
class ReviewResult:
    passed: bool
    violations: list[str] = field(default_factory=list)
    line_count: int = 0


def review_file(content: str, filename: str) -> ReviewResult:
    violations: list[str] = []

    for pattern, reason in _FORBIDDEN_PATTERNS:
        if re.search(pattern, content):
            violations.append(f"{filename}: {reason}")

    for pattern, reason in _REQUIRED_PATTERNS:
        if not re.search(pattern, content):
            violations.append(f"{filename}: {reason}")

    line_count = content.count("\n") + 1
    if line_count > _MAX_LINES:
        violations.append(
            f"{filename}: {line_count} lines exceeds the {_MAX_LINES}-line guideline for a single page/flow file — split it"
        )

    return ReviewResult(passed=not violations, violations=violations, line_count=line_count)
