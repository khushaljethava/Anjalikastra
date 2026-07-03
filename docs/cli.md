# CLI Reference

```
webtest-agent <url> [options]
```

Also available as `python -m webtest_agent <url>`.

## Arguments

| Argument | Description |
|---|---|
| `<url>` | Target site URL, e.g. `https://example.com`. Must include the scheme. |

## Options

| Option | Default | Description |
|---|---|---|
| `--output-dir PATH` | `output/` | Where run artifacts (report + suite) are written. |
| `--max-pages N` | `40` | Cap on pages crawled. The report notes when the crawl was truncated by this cap. |
| `--throttle-ms N` | `500` | Minimum delay between requests to the target, in milliseconds. Applies to both the HTTP crawl and browser-based endpoint capture. |
| `--openapi PATH` | none | OpenAPI 3.x spec (JSON or YAML) to enrich endpoint discovery. Documented endpoints are merged with observed traffic; never required. |
| `--public-only` / `--allow-auth` | `--public-only` | v1 crawls only unauthenticated, public pages. Auth-gated areas are reported as *not covered*, never falsely passed. |
| `--dry-run` | off | Print the run plan (scope, throttle, provider, models) and exit without any network requests. |
| `--resume RUN_ID` | none | Resume a previous run. Reuses `output/<run-id>` and skips discovery if it already completed — see [Caching & Resuming](caching-resuming.md). |
| `--llm-provider NAME` | auto | `anthropic` or `openai` (any OpenAI-compatible endpoint). Auto-detected from credentials when omitted — see [LLM Providers](providers.md). |
| `--cheap-model NAME` | `claude-haiku-4-5-20251001` | Model for classification and routine summaries. |
| `--capable-model NAME` | `claude-sonnet-5` | Model for test generation and failure triage. |
| `--verbose`, `-v` | off | Debug-level logging, including per-call LLM token usage lines. |

## Environment variables

| Variable | Effect |
|---|---|
| `ANTHROPIC_API_KEY` | Enables the `anthropic` provider (auto-detected). |
| `OPENAI_API_KEY` | Enables the `openai` provider (auto-detected). |
| `OPENAI_BASE_URL` | Points the `openai` provider at any compatible server (Ollama, OpenRouter, Gemini, vLLM, ...). Setting this alone also auto-selects `openai` — no key needed for local servers. |
| `WEBTEST_AGENT_LLM_PROVIDER` | Explicit provider choice; same values as `--llm-provider`. |
| `WEBTEST_AGENT_CHEAP_MODEL` | Default for `--cheap-model`. |
| `WEBTEST_AGENT_CAPABLE_MODEL` | Default for `--capable-model`. |
| `WEBTEST_AGENT_CHROMIUM_PATH` | Use a pre-installed Chromium binary instead of one downloaded by `playwright install` (offline installs, CI images). |

Precedence everywhere: **CLI flag → environment variable → built-in default.**

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Run completed; generated suite passed (or wasn't executed by request). |
| `1` | Run completed with failures — generated tests failed, no pages were reachable, or the pipeline aborted partway (a partial report is still written). |
| `2` | Invalid arguments (bad URL, unknown provider, missing OpenAPI file, ...). |
| `130` | Interrupted (Ctrl-C). Partial state is saved; use `--resume`. |
