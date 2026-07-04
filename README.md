# Anjalikastra

An open-source CLI that points at a live website URL and produces:

1. A **human-readable report** — pass/fail per page and endpoint, coverage %,
   and a drafted list of likely bugs, queued for human review.
2. A **runnable end-to-end / functional test suite** (TypeScript + Playwright Test)
   — organized test files, config, README, and dependency manifest — that installs
   and runs with a single command on first try.

The tool discovers what to test by crawling from the URL you give it. It has no
access to the target's source code, repo, or CI — everything is inferred from the
live site, treating every target as black-box.

These are **end-to-end / functional / smoke tests**, not unit tests — unit tests
require source access, and this tool never has that.

**Full documentation:** https://khushaljethava.github.io/Anjalikastra/ (built
from [`website/`](website/) with Astro Starlight — deploys automatically from `main`).

## Install

```bash
pip install anjalikastra
playwright install --with-deps chromium   # for the tool's own crawler/endpoint capture
```

Or from source (see [Developing this tool](#developing-this-tool)).

Configure an LLM for full-quality classification and generation: set
`ANTHROPIC_API_KEY` for Claude, or `OPENAI_API_KEY`/`OPENAI_BASE_URL` for any
OpenAI-compatible provider — OpenAI, Ollama, OpenRouter, Gemini, and more (see
"Configuring LLM models" below). Without any key, the tool still runs end-to-end
using a heuristic/template-only fallback — smaller and less targeted, but still
a working suite.

## Usage

```bash
anjalikastra https://example.com
```

```
anjalikastra <url> [options]

  --output-dir PATH     Where run artifacts are written (default: output/)
  --max-pages N         Cap on pages crawled (default: 40)
  --throttle-ms N       Minimum delay between requests, in ms (default: 500)
  --openapi PATH        Optional OpenAPI spec to enrich endpoint discovery
  --public-only / --allow-auth   v1: only crawl unauthenticated pages (default: on)
  --dry-run             Print the plan and exit without making network requests
  --resume RUN_ID        Resume a previous run (output/<run-id>), skipping discovery if it already finished
  --cheap-model NAME     Model for classification/summaries (default: claude-haiku-4-5-20251001)
  --capable-model NAME   Model for test generation/triage (default: claude-sonnet-5)
  --llm-provider NAME    'anthropic' or 'openai' (any OpenAI-compatible endpoint); auto-detected by default
  --verbose, -v          Verbose logging
```

Run `anjalikastra <url> --dry-run` first on a new target — it prints exactly what
the tool would do (crawl scope, throttle, model routing) without making a single
network request.

### Resuming a crashed or interrupted run

Discovery (crawling + endpoint capture) is checkpointed to `output/<run-id>/checkpoint.json`.
If the process crashes or is interrupted after discovery completes, resume with:

```bash
anjalikastra <url> --resume <run-id>
```

This skips re-crawling the site — avoiding hitting the target's infrastructure a
second time — and picks up from classification/generation. Classification results
are also cached independently by content-hash (see "How it works" below), so even
a fresh run against an unchanged site is cheap.

## What you get

```
output/<run-id>/
├── report.md          # human-readable: coverage, failures, drafted bugs, cost
├── report.json         # same data, machine-readable
└── suite/               # the deliverable — yours to keep and maintain
    ├── package.json
    ├── playwright.config.ts
    ├── README.md
    └── tests/
        ├── pages/*.spec.ts
        └── api/*.spec.ts
```

Run the generated suite:

```bash
cd output/<run-id>/suite
npm install && npx playwright install --with-deps chromium
npm test
```

## Coverage honesty

The report always states "tested N of M known pages" and lists what wasn't
reached — auth-gated, blocked by robots.txt, sitemap-only, or crawl-truncated —
next to *why*. There is no bare green checkmark implying full coverage.

## Scope (v1)

- Crawls and tests **public pages only**. Login-gated flows are not tested;
  they're reported as "not covered," never silently skipped or falsely passed.
  See `anjalikastra/discovery/auth.py` for the v2 design.
- No bot-detection evasion. If a target blocks the crawler, the tool tells you to
  allowlist its User-Agent on your own site rather than trying to get around it.
- Nothing is auto-filed or auto-fixed. The tool drafts a bug list; a human decides.

## How it works

```
URL -> Discovery (sitemap + crawl + network capture)
    -> Analysis (page/endpoint classification)
    -> Test generation (assertions -> Playwright files -> review gate)
    -> Execution (run the suite, capture baseline)
    -> Triage (classify failures, draft bug reports)
    -> Reporting (report.md / report.json)
```

Classification and routine summaries use a cheap/small model; test generation and
failure triage use a more capable model. A content-hash cache under
`output/.cache/` means a second run against an unchanged page skips re-classifying
and re-generating it — see the "Cost" section of `report.md` for the token delta.

## Configuring LLM models

The tool splits LLM work across two tiers, each independently configurable:

| Tier | Used for | Default | Override |
|---|---|---|---|
| cheap | page/endpoint classification, routine summaries | `claude-haiku-4-5-20251001` | `--cheap-model` flag or `ANJALIKASTRA_CHEAP_MODEL` env var |
| capable | test generation, failure triage | `claude-sonnet-5` | `--capable-model` flag or `ANJALIKASTRA_CAPABLE_MODEL` env var |

```bash
export ANTHROPIC_API_KEY=sk-ant-...
anjalikastra https://example.com \
  --cheap-model claude-haiku-4-5-20251001 \
  --capable-model claude-opus-4-8
```

CLI flags take precedence over env vars; env vars take precedence over the defaults.
`--dry-run` shows exactly which models a run would use.

### Supported providers

Two backends are supported natively, selected with `--llm-provider` (or
`ANJALIKASTRA_LLM_PROVIDER`), and auto-detected from your credentials if you
don't specify one:

| Provider | Covers | Credentials |
|---|---|---|
| `anthropic` | Claude models via the Anthropic API | `ANTHROPIC_API_KEY` |
| `openai` | **any OpenAI-compatible endpoint**: OpenAI, Ollama (local models), OpenRouter, Gemini, vLLM, LM Studio, ... | `OPENAI_API_KEY` and/or `OPENAI_BASE_URL` |

Auto-detection: `ANTHROPIC_API_KEY` set → `anthropic`; otherwise
`OPENAI_API_KEY` or `OPENAI_BASE_URL` set → `openai`; neither → heuristic mode.
When using a non-Anthropic provider, pass model names your endpoint actually
serves via `--cheap-model` / `--capable-model`.

**OpenAI:**

```bash
export OPENAI_API_KEY=sk-...
anjalikastra https://example.com --cheap-model gpt-5-mini --capable-model gpt-5
```

**Ollama (local models, no API key needed):**

```bash
export OPENAI_BASE_URL=http://localhost:11434/v1
anjalikastra https://example.com --cheap-model llama3.2 --capable-model qwen2.5-coder:32b
```

**OpenRouter (one key, hundreds of models):**

```bash
export OPENAI_BASE_URL=https://openrouter.ai/api/v1
export OPENAI_API_KEY=sk-or-...
anjalikastra https://example.com \
  --cheap-model google/gemini-2.5-flash --capable-model anthropic/claude-sonnet-4.5
```

**Gemini (via Google's OpenAI-compatible endpoint):**

```bash
export OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
export OPENAI_API_KEY=your-gemini-api-key
anjalikastra https://example.com --cheap-model gemini-2.5-flash --capable-model gemini-2.5-pro
```

Any other server that speaks the OpenAI Chat Completions protocol (vLLM,
LM Studio, LiteLLM proxy, Together, Groq, ...) works the same way: set
`OPENAI_BASE_URL` to its address and pass its model names.
`--dry-run` shows the resolved provider, base URL, and models before anything runs.

**No key at all?** The tool still runs end-to-end in heuristic/template-only
mode — classification falls back to URL/DOM heuristics and generation uses the
deterministic templates. The suite is smaller and less targeted but still valid
and runnable.

## Developing this tool

```bash
pip install -e ".[dev]"
pytest
```

`anjalikastra/` is the Python orchestrator; it emits TypeScript/Playwright as
output artifacts. See `anjalikastra/generation/review_gate.py` for the
minimal-code discipline applied to every generated test file before it ships.
