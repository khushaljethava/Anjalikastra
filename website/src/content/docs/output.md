---
title: Reports & Output
description: What Anjalikastra writes to output/ — coverage reports, JSON data, and the generated Playwright test suite.
sidebar:
  order: 5
---

Every run writes to `output/<run-id>/`:

```
output/<run-id>/
├── report.md
├── report.json
├── checkpoint.json
└── suite/
    ├── package.json
    ├── playwright.config.ts
    ├── README.md
    └── tests/
        ├── pages/*.spec.ts
        └── api/*.spec.ts
```

## Coverage — always with a denominator

```markdown
## Coverage

**Tested 24 of 31 known pages (77.4%).**

### Not reached

| URL | Reason |
|---|---|
| https://site/account | disallowed by robots.txt |
| https://site/old-page | sitemap entry never fetched |
```

Nothing is silently dropped. Every missing page has a reason.

## Test results and drafted bugs

Failures appear with triage classification, confidence, steps, expected vs actual.
**Nothing is auto-filed to an issue tracker.**

## report.json

Same data as structured JSON — pipe into dashboards or CI:

```bash
jq '.coverage.coverage_percent' output/<run-id>/report.json
```

## The generated suite

- One spec per page under `tests/pages/`, one per API resource under `tests/api/`.
- Idiomatic Playwright — web-first assertions, no manual sleeps.
- Re-point with `BASE_URL` for staging without edits.

Edit tests directly or re-run Anjalikastra — the cache makes regeneration cheap.
