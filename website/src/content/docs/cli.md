---
title: CLI Reference
description: Full command-line reference for anjalikastra — flags, environment variables, and exit codes.
sidebar:
  order: 2
---

```
anjalikastra <url> [options]
```

Also available as `python -m anjalikastra <url>`.

## Arguments

| Argument | Description |
|---|---|
| `<url>` | Target site URL, e.g. `https://example.com`. Must include the scheme. |

## Options

| Option | Default | Description |
|---|---|---|
| `--output-dir PATH` | `output/` | Where run artifacts (report + suite) are written. |
| `--max-pages N` | `40` | Cap on pages crawled. The report notes when truncated. |
| `--throttle-ms N` | `500` | Minimum delay between requests, in milliseconds. |
| `--openapi PATH` | none | OpenAPI 3.x spec to enrich endpoint discovery. |
| `--public-only` / `--allow-auth` | `--public-only` | v1: public pages only. Auth-gated areas reported as not covered. |
| `--dry-run` | off | Print the run plan and exit without network requests. |
| `--resume RUN_ID` | none | Resume a previous run — see [Caching & Resuming](/caching-resuming/). |
| `--llm-provider NAME` | auto | `anthropic` or `openai` (OpenAI-compatible). Auto-detected from credentials. |
| `--cheap-model NAME` | `claude-haiku-4-5-20251001` | Model for classification and summaries. |
| `--capable-model NAME` | `claude-sonnet-5` | Model for test generation and triage. |
| `--verbose`, `-v` | off | Debug logging including LLM token usage. |

## Environment variables

| Variable | Effect |
|---|---|
| `ANTHROPIC_API_KEY` | Enables the `anthropic` provider (auto-detected). |
| `OPENAI_API_KEY` | Enables the `openai` provider (auto-detected). |
| `OPENAI_BASE_URL` | OpenAI-compatible endpoint (Ollama, OpenRouter, Gemini, vLLM, …). |
| `ANJALIKASTRA_LLM_PROVIDER` | Explicit provider; same values as `--llm-provider`. |
| `WEBTEST_AGENT_CHEAP_MODEL` | Default for `--cheap-model`. |
| `ANJALIKASTRA_CAPABLE_MODEL` | Default for `--capable-model`. |
| `ANJALIKASTRA_CHROMIUM_PATH` | Pre-installed Chromium binary for offline/CI use. |

Precedence: **CLI flag → environment variable → built-in default.**

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Run completed; generated suite passed. |
| `1` | Failures or pipeline abort (partial report still written). |
| `2` | Invalid arguments. |
| `130` | Interrupted (Ctrl-C). Use `--resume` to continue. |
