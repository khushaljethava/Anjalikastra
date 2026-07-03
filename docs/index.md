# Anjalikastra

**Point it at a URL. Get back a runnable Playwright E2E test suite and an honest report.**

![Anjalikastra — crawl a site, get a passing test suite](assets/hero.png)

Anjalikastra is an open-source CLI that tests live websites black-box — no access
to the target's source code, repo, or CI. It crawls from the URL you give it,
figures out what to test, and produces two deliverables:

1. **A human-readable report** — pass/fail per page and endpoint, coverage %, and
   a drafted list of likely bugs, queued for human review (never auto-filed).
2. **A runnable end-to-end test suite** — TypeScript + Playwright Test, organized
   by page and API resource, with a config, README, and dependency manifest that
   run cleanly with a single command on first try.

```bash
pip install anjalikastra
anjalikastra https://your-site.example
```

!!! note "E2E tests, not unit tests"
    Unit tests require source access, and this tool never has that. Everything it
    emits is an **end-to-end / functional / smoke test** driven against the live site.

## Why Anjalikastra?

- **Zero setup on the target.** No SDK to install, no CI integration, no repo
  access. If a browser can reach the site, Anjalikastra can test it.
- **The suite is yours to keep.** Generated tests are idiomatic Playwright —
  web-first assertions, no page-object bloat, no hand-rolled waits — and every
  file passes a minimal-code review gate before it ships. Edit them like
  hand-written tests.
- **Honest coverage, always.** The report states *"tested N of M known pages"*
  and lists every page it couldn't reach, with the reason — auth-gated, blocked
  by robots.txt, crawl-truncated. No bare green checkmark implying full coverage.
- **Bring your own LLM.** Anthropic Claude natively, plus any OpenAI-compatible
  endpoint: OpenAI, Ollama local models, OpenRouter, Gemini, vLLM, LM Studio.
  No key at all? A heuristic fallback still produces a working suite.
- **Respectful by design.** Throttled crawling, robots.txt respected, no
  bot-detection evasion, no CAPTCHA solving. Test *your own* sites.

## The pipeline at a glance

```
URL ─▶ Discovery   sitemap + BFS crawl + browser network capture
   ─▶ Analysis    classify each page/endpoint type (cheap model)
   ─▶ Generation  infer assertions → emit Playwright files → review gate
   ─▶ Execution   run the suite, capture DOM/screenshot baselines
   ─▶ Triage      classify failures, draft bug reports (capable model)
   ─▶ Report      report.md + report.json with coverage accounting
```

Read [How It Works](how-it-works.md) for the full walkthrough, or jump straight
to [Getting Started](getting-started.md).
