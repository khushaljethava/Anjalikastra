# Contributing

## Development setup

```bash
git clone https://github.com/khushaljethava/Anjalikastra
cd Anjalikastra
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install --with-deps chromium
```

## Running the tests

```bash
pytest
```

The suite includes browser-driven integration tests (full pipeline against a
local fixture site, `--resume` behavior). They're skipped unless
`WEBTEST_AGENT_CHROMIUM_PATH` points at a Chromium binary:

```bash
export WEBTEST_AGENT_CHROMIUM_PATH=$(python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    print(p.chromium.executable_path)
")
pytest
```

CI (GitHub Actions) runs the full suite, integration tests included, on
Python 3.10 and 3.12.

## Project layout

```
anjalikastra/
├── cli.py                # entrypoint & argument validation
├── config.py             # every tunable, centralized
├── orchestrator.py       # wires the pipeline stages together
├── checkpoint.py         # discovery checkpointing (--resume)
├── discovery/            # sitemap, crawler, endpoint capture, auth (v2 design)
├── analysis/             # page/endpoint classification
├── generation/           # assertions, codegen, templates, review gate
├── execution/            # suite runner, DOM/screenshot baselines
├── triage/               # failure classification, bug drafting
├── reporting/            # coverage accounting, report rendering
├── cache/                # content-hash cache store
└── llm/                  # provider clients (anthropic / openai-compatible)
tests/                    # the tool's own tests, incl. fixture site
docs/                     # this documentation (MkDocs)
```

## The code-discipline ladder

All code — the tool's own source *and* every test file it emits — follows a
minimal-code ladder. Before writing anything, stop at the first rung that applies:

1. Does this need to exist at all?
2. Already present in the codebase? Reuse it.
3. Standard library does it? Use the stdlib.
4. Native framework feature (Playwright web-first assertions, fixtures)? Use it.
5. Already an installed dependency? Use it.
6. Fits in one line? Write one line.
7. Only then: the minimum code that actually works.

Never shrink or skip input validation, error handling, or security. Be lazy
about the *solution*, never about understanding the *problem*.

For generated test files this is enforced mechanically by
`generation/review_gate.py` — model output that hand-rolls waits, wraps
assertions, or builds page objects for single-use pages is rejected and the
deterministic draft ships instead. PRs to the tool itself are held to the same
standard by review.

## Terminology

Use **E2E test**, **functional test**, or **smoke test** everywhere — code,
docs, CLI text. Never "unit test": unit tests require source access, and this
tool never has it.

## Working on the docs

```bash
pip install mkdocs-material
mkdocs serve        # live-reload at http://127.0.0.1:8000
```

Docs deploy to GitHub Pages automatically when changes to `docs/` or
`mkdocs.yml` land on `main`.
