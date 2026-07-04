---
title: How It Works
description: ""
sidebar:
  order: 4
---

---
title: How It Works
weight: 4
---

Everything is inferred from the live site — the tool treats every target as
black-box. The pipeline is six stages, each feeding the next.

## 1. Discovery

**Sitemap as a seed list, not truth.** `sitemap.xml` (and sitemap index files)
are fetched and parsed, but sitemaps are routinely stale and incomplete — their
URLs only seed the crawl. Sitemap entries that are never actually reached are
reported as *not covered*, not assumed fine.

**Throttled BFS crawl.** From the seeds, a breadth-first crawl follows
same-origin links up to `--max-pages`, respecting `robots.txt` and enforcing a
minimum delay between requests (`--throttle-ms`). Each page records its final
URL, status, load time, and how it was found (sitemap, crawl, or both).

**Endpoint capture in a real browser.** The reachable pages are then loaded in
headless Chromium while the tool records every XHR/`fetch` request the pages
fire — this is the API surface the site *actually uses*. Numeric, UUID and
ObjectId path segments collapse to `:id` so `/users/42` and `/users/91` become
one endpoint. An optional `--openapi` spec merges in documented endpoints.

## 2. Analysis

Each page is classified by type — login, listing, detail, checkout, form,
article, dashboard, error, ... — and each endpoint as read/mutation/auth/health.
Classification drives *targeted* assertions later: a checkout page and a blog
post need very different checks.

This is cheap-model work, cached by content-hash, and every label carries a
confidence score. Low-confidence classifications get generic assertions rather
than wrong specific ones.

## 3. Generation

**Deterministic draft first.** From page content + type, the tool infers what
"correct" means — healthy status, expected title and heading, visible nav, no
console errors, load under a threshold, required form fields marked; for
endpoints, expected status, JSON shape, and negative cases (unknown id, missing
auth). A template renders these into a valid Playwright file. This draft is what
guarantees the suite runs on first try even with no LLM configured.

**LLM enhancement, gated.** When a capable model is available, it's given the
draft and asked to improve it into more thorough, idiomatic test code. The
enhanced version ships **only if it survives the review gate**; otherwise the
deterministic draft ships instead.

**The review gate.** Every generated file — LLM or template — is checked against
a minimal-code discipline: no `waitForTimeout` sleeps, no manual polling loops,
no page-object classes for single-use pages, no hand-rolled assertion wrappers,
no oversized files. Users keep and maintain these files, so bloat here is
exactly the maintenance burden the tool exists to remove.

The suite lands as a complete Playwright project: `tests/pages/*.spec.ts`,
`tests/api/*.spec.ts`, `playwright.config.ts`, `package.json`, and a README.

## 4. Execution & baseline

The generated suite runs via the normal Playwright CLI (`npm install`,
`npx playwright test`), collecting pass/fail, durations, and errors.

Separately, each tested page's DOM structure and a full-page screenshot are
stored as a **baseline**. On later runs the current structure is diffed against
it, catching regressions no explicit assertion anticipated. Volatile content —
timestamps, "3 minutes ago" strings, ad/banner containers — is normalized out
before hashing to suppress false positives; whatever noise survives is absorbed
by triage rather than hard-failing.

## 5. Triage

Each failure is classified as **regression / flake / expected-change /
needs-human-review** (capable model, with a conservative heuristic fallback).
The bias is deliberate: when uncertain, flag it — a wrong "all clear" costs far
more trust than a false alarm.

Likely regressions get a structured draft bug: steps, expected vs. actual,
affected page/endpoint. Drafts are **queued for human review, never auto-filed**.

## 6. Reporting

`report.md` (human) and `report.json` (machine) always include:

- **Coverage with a denominator**: "tested N of M known pages", plus every
  unreached URL and *why* (auth-gated, robots.txt, crawl truncated, fetch failed).
- Test results with failure details.
- The drafted-bugs queue.
- The generated-suite inventory (file, source: llm/deterministic, line count).
- Cost: provider, per-tier calls and tokens, cache hit rate.

## Design boundaries

- **No bot-detection evasion, no CAPTCHA solving.** If bot protection blocks the
  crawler, the tool says so and tells you to allowlist its User-Agent on your
  own site.
- **No auto-filing, no auto-fixing, no deploy gating.** The tool drafts; a human
  decides.
- **v1 is public pages only.** Auth-gated flows are reported as not covered.
  The authenticated-crawling design for v2 lives in `anjalikastra/discovery/auth.py`,
  and the coverage model already accounts for it.
