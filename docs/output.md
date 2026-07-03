# Reports & Generated Suite

Every run writes to `output/<run-id>/`:

```
output/<run-id>/
├── report.md          # human-readable report
├── report.json         # same data, machine-readable
├── checkpoint.json     # discovery checkpoint (enables --resume)
└── suite/               # the deliverable test suite
    ├── package.json
    ├── playwright.config.ts
    ├── README.md
    └── tests/
        ├── pages/*.spec.ts    # one file per page
        └── api/*.spec.ts      # one file per API resource
```

## The report

### Coverage — always with a denominator

```markdown
## Coverage

**Tested 24 of 31 known pages (77.4%).**

### Not reached

| URL | Reason |
|---|---|
| https://site/account   | disallowed by robots.txt |
| https://site/old-page  | listed in sitemap.xml but never fetched (max-pages cap or unreachable) |
| https://site/broken    | returned HTTP 500 |
```

"Known pages" counts everything the tool learned about — crawled pages,
robots-blocked URLs, and sitemap entries it never reached. If the crawl hit the
`--max-pages` cap, the report says so. A page missing from the suite is always
listed with a reason; nothing is silently dropped.

### Test results and drafted bugs

Failures appear in a results table, then each one gets a triage entry:

```markdown
### GET /api/cart returns 200 — regression

- **Affected:** tests/api/api-cart.spec.ts
- **Classification:** regression (confidence 0.82)
- **Steps:** Run `GET /api/cart returns 200` in tests/api/api-cart.spec.ts
- **Expected:** 200 with keys: items, total
- **Actual:** 500 Internal Server Error
```

Structural changes caught by the DOM baseline diff appear here too, classified
`needs_human_review`. **Nothing is ever filed to an issue tracker automatically.**

### Cost

Provider, per-tier model calls, token totals, and cache hit rate — so you can
see exactly what a run cost and how much the cache saved on re-runs.

## report.json

The same data as structured JSON — coverage (with per-URL reasons), every test
result, drafted bugs, the suite file inventory, and cost — for piping into
dashboards or CI checks:

```bash
jq '.coverage.coverage_percent' output/<run-id>/report.json
jq '.draft_bugs[] | select(.classification == "regression")' output/<run-id>/report.json
```

## The generated suite

The suite is a self-contained, standard Playwright project designed to be
**kept and maintained**, not regenerated on every change:

- **Organized by page/flow** — one spec file per page under `tests/pages/`, one
  per API resource under `tests/api/`. No monolithic files.
- **Idiomatic Playwright** — web-first assertions (`toHaveTitle`, `toBeVisible`,
  `toContainText`), built-in fixtures, no manual sleeps or wait loops.
- **Review-gated** — every file passed the minimal-code gate before shipping.
  The report notes each file's source: `llm` (model-enhanced) or
  `deterministic` (template).
- **Configurable target** — `BASE_URL` env var re-points the whole suite at
  another environment without edits.

A generated page spec looks like this:

```typescript
import { test, expect } from '@playwright/test';

test.describe('login: /login', () => {
  test('loads with a healthy status', async ({ page }) => {
    const response = await page.goto('https://site/login');
    expect(response?.status()).toBeLessThan(400);
  });

  test('has the expected title', async ({ page }) => {
    await page.goto('https://site/login');
    await expect(page).toHaveTitle('Login');
  });

  test('form #1 marks its required fields', async ({ page }) => {
    await page.goto('https://site/login');
    const form = page.locator('form').nth(0);
    await expect(form.locator('[name="email"], #email').first()).toHaveAttribute('required', '');
    await expect(form.locator('[name="password"], #password').first()).toHaveAttribute('required', '');
  });
});
```

If the suite drifts out of date as the site evolves, either edit it directly
(it's plain Playwright) or re-run Anjalikastra to regenerate against the
current site — the cache makes regeneration cheap for unchanged pages.
