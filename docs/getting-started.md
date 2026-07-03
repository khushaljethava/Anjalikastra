# Getting Started

## Requirements

- Python 3.10+
- Node.js 18+ (to run the generated Playwright suite)
- Optionally, an LLM API key — see [LLM Providers](providers.md). Without one,
  the tool runs in heuristic/template-only mode.

## Install

```bash
git clone https://github.com/khushaljethava/Anjalikastra
cd Anjalikastra
pip install -e .
python -m playwright install --with-deps chromium   # browser for the crawler
```

## First run

Always start with a dry run — it prints exactly what the tool *would* do
(crawl scope, throttle, resolved LLM provider and models) without a single
network request to the target:

```bash
webtest-agent https://your-site.example --dry-run
```

Then run for real:

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # or see LLM Providers for alternatives
webtest-agent https://your-site.example
```

A run works through discovery → classification → generation → execution →
triage, and finishes by printing the report location, coverage, and token cost:

```
Report: output/20260703-120000/report.md
Coverage: 24/31 pages (77.4%)
Tokens: cheap model: 24 calls, ... | capable model: 12 calls, ...
```

## Run the generated suite

The suite is a normal Playwright project — the tool already ran it once, and
you can run it yourself anytime:

```bash
cd output/<run-id>/suite
npm install
npx playwright install --with-deps chromium
npm test
```

Point the same suite at another environment with `BASE_URL`:

```bash
BASE_URL=https://staging.your-site.example npm test
```

## Testing your own site

webtest-agent is built for testing **sites you own or are authorized to test**:

- Requests are throttled (default 500 ms between requests) and `robots.txt` is
  respected, so a run behaves like a polite crawler, not a load test.
- If your site's bot protection blocks the crawler, the fix is to **allowlist
  the tool's User-Agent** (`webtest-agent/0.1 ...`) on your own infrastructure.
  The tool will never try to evade detection.

Next: the full [CLI Reference](cli.md).
