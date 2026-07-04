---
title: How It Works
description: Six-stage pipeline — discovery, analysis, generation, execution, triage, and reporting — all from a live URL with no source access.
sidebar:
  order: 4
---

Everything is inferred from the live site — black-box, no repo or CI access.

## 1. Discovery

- **Sitemap** seeds the crawl but is not treated as truth — stale URLs are reported as not covered.
- **BFS crawl** follows same-origin links up to `--max-pages`, respecting `robots.txt` and throttle.
- **Browser capture** records XHR/fetch traffic in headless Chromium; path segments normalize to `:id`.

## 2. Analysis

Pages classified by type (login, listing, checkout, form, …) and endpoints as read/mutation/auth.
Cheap-model work, cached by content-hash. Low-confidence labels get generic assertions.

## 3. Generation

Deterministic Playwright draft first — guarantees a runnable suite without an LLM.
Capable model may enhance the draft; enhanced version ships only if it passes the review gate
(no `waitForTimeout`, no page-object bloat, no hand-rolled waits).

Output: `tests/pages/*.spec.ts`, `tests/api/*.spec.ts`, config, README.

## 4. Execution

Suite runs via Playwright CLI. DOM structure and screenshots stored as baselines for regression diffing.

## 5. Triage

Failures classified as regression / flake / expected-change / needs-human-review.
Likely regressions get draft bug reports — queued for human review, never auto-filed.

## 6. Reporting

`report.md` and `report.json` include coverage with denominator, test results, drafted bugs,
suite inventory, and token cost.

## Design boundaries

- No bot-detection evasion or CAPTCHA solving.
- No auto-filing or auto-fixing.
- v1: public pages only. Auth-gated flows reported as not covered.
