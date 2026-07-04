---
title: Getting Started
description: Install Anjalikastra, run your first crawl, and execute the generated Playwright E2E test suite in minutes.
sidebar:
  order: 1
---

## Requirements

- Python 3.10+
- Node.js 18+ (to run the generated Playwright suite)
- Optional LLM API key — see [LLM Providers](/providers/). Without one, heuristic mode still works.

## Install

```bash
pip install anjalikastra
python -m playwright install --with-deps chromium
```

Or from source:

```bash
git clone https://github.com/khushaljethava/Anjalikastra
cd Anjalikastra
pip install -e .
python -m playwright install --with-deps chromium
```

## First run

Start with a dry run — it prints crawl scope, throttle, and resolved LLM settings
without hitting the target:

```bash
anjalikastra https://your-site.example --dry-run
```

Then run for real:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
anjalikastra https://your-site.example
```

Output includes report path, coverage, and token cost:

```
Report: output/20260703-120000/report.md
Coverage: 24/31 pages (77.4%)
```

## Run the generated suite

```bash
cd output/<run-id>/suite
npm install
npx playwright install --with-deps chromium
npm test
```

Point at staging with `BASE_URL`:

```bash
BASE_URL=https://staging.your-site.example npm test
```

## Test sites you own

Anjalikastra is built for **sites you own or are authorized to test**:

- Requests are throttled (default 500 ms) and `robots.txt` is respected.
- If bot protection blocks the crawler, allowlist User-Agent `Anjalikastra/0.1` on your infrastructure.

Next: [CLI Reference](/cli/).
