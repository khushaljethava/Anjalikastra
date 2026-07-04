---
title: Contributing
description: Development setup, project layout, and coding standards for contributing to Anjalikastra.
sidebar:
  order: 8
---

## Development setup

```bash
git clone https://github.com/khushaljethava/Anjalikastra
cd Anjalikastra
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install --with-deps chromium
```

## Running tests

```bash
pytest
```

Integration tests need Chromium:

```bash
export ANJALIKASTRA_CHROMIUM_PATH=$(python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    print(p.chromium.executable_path)
")
pytest
```

## Project layout

```
anjalikastra/
├── cli.py              # entrypoint
├── orchestrator.py     # pipeline wiring
├── discovery/          # sitemap, crawler, endpoints
├── analysis/           # classification
├── generation/         # assertions, codegen, review gate
├── execution/          # suite runner, baselines
├── triage/             # failure classification
├── reporting/          # coverage, reports
└── llm/                # provider clients
website/                # docs site (Astro Starlight → GitHub Pages)
```

## Working on the docs

```bash
cd website
npm install
npm run dev      # http://localhost:4321
npm run build    # output to website/dist
```

Docs deploy to GitHub Pages automatically when `website/` changes land on `main`.

## Terminology

Use **E2E test**, **functional test**, or **smoke test** — never "unit test".
