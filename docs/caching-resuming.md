# Caching & Resuming

Two independent mechanisms keep repeat runs fast, cheap, and gentle on the
target site.

## Content-hash cache (across runs)

Classification results are cached under `<output-dir>/.cache/`, keyed by
**URL + content-hash**. On any later run — same run or a fresh one — a page
whose content hasn't changed skips its LLM classification entirely and reuses
the cached result.

Practical effect: a second run against an unchanged site makes near-zero model
calls and completes materially faster and cheaper. The report's Cost section
shows the cache hit rate and per-tier token totals, so the savings are visible,
not assumed.

DOM/screenshot baselines live next to it under `<output-dir>/.baseline/` and
also persist across runs — that's what makes regression diffing possible.

To start completely fresh, delete `.cache/` and `.baseline/` from your output
directory.

## Checkpointing & `--resume` (within a run)

Discovery — the crawl plus browser-based endpoint capture — is the phase that's
most expensive to redo and the only one that hits the target's infrastructure.
When it completes, its results are checkpointed to
`output/<run-id>/checkpoint.json`.

If the run crashes or is interrupted afterwards, resume it:

```bash
Anjalikastra https://your-site.example --resume <run-id>
```

The resumed run reuses the checkpointed crawl and endpoint data — **zero new
requests to the target for discovery** — and picks up from classification.
Combined with the content-hash cache, resuming is nearly free.

When a run fails partway, the CLI prints the exact resume command, and the
partial report notes it too.

!!! tip "Crawl politeness is the point"
    Both mechanisms exist for the same reason the throttle does: a testing tool
    shouldn't hammer the site it's testing. Re-running because of a crash or an
    unchanged page shouldn't cost the target anything.
