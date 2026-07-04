---
title: Caching & Resuming
description: Content-hash caching and checkpoint resume keep repeat runs fast, cheap, and gentle on target sites.
sidebar:
  order: 6
---

## Content-hash cache

Classification cached under `<output-dir>/.cache/`, keyed by URL + content-hash.
Unchanged pages skip LLM calls on later runs. Baselines live in `.baseline/` for regression diffing.

Delete `.cache/` and `.baseline/` to start fresh.

## Checkpointing & `--resume`

Discovery is checkpointed to `output/<run-id>/checkpoint.json`. After a crash:

```bash
anjalikastra https://your-site.example --resume <run-id>
```

Resumed runs reuse crawl data — zero new discovery requests — and pick up from classification.
