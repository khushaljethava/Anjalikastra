---
title: Anjalikastra
description: Open-source CLI that crawls any live website and generates a runnable Playwright E2E test suite plus an honest coverage report.
template: splash
hero:
  tagline: Point it at a URL. Get a runnable Playwright test suite.
  image:
    file: ../../assets/hero.svg
    alt: Anjalikastra — autonomous web testing
  actions:
    - text: Get Started
      link: /getting-started/
      icon: right-arrow
      variant: primary
    - text: How It Works
      link: /how-it-works/
      icon: open-book
    - text: View on GitHub
      link: https://github.com/khushaljethava/Anjalikastra
      icon: external
      attrs:
        target: _blank
---

**Anjalikastra** is an open-source CLI that tests live websites black-box — no source
code, repo, or CI access required. It crawls from the URL you give it and produces:

1. **A human-readable report** — pass/fail per page and endpoint, coverage %, and
   drafted likely bugs queued for human review.
2. **A runnable E2E test suite** — TypeScript + Playwright Test, organized by page
   and API resource, ready to run with one command.

```bash
pip install anjalikastra
anjalikastra https://your-site.example
```

> [!NOTE]
> **E2E tests, not unit tests**
> Unit tests require source access. Anjalikastra emits **end-to-end / functional /
> smoke tests** driven against the live site.

## Why Anjalikastra?

- **Zero setup on the target** — no SDK, no CI integration, no repo access.
- **The suite is yours to keep** — idiomatic Playwright with a minimal-code review gate.
- **Honest coverage** — reports *"tested N of M known pages"* with reasons for gaps.
- **Bring your own LLM** — Claude, OpenAI, Ollama, OpenRouter, Gemini, or heuristic fallback.
- **Respectful by design** — throttled crawling, robots.txt respected, no bot evasion.

## Pipeline at a glance

```
URL → Discovery → Analysis → Generation → Execution → Triage → Report
```
