---
title: LLM Providers
weight: 3
---

Anjalikastra splits LLM work across two tiers so routine work stays cheap:

| Tier | Used for | Default model |
|---|---|---|
| **cheap** | page/endpoint classification, routine summaries | `claude-haiku-4-5-20251001` |
| **capable** | test generation, failure triage | `claude-sonnet-5` |

Override either with `--cheap-model` / `--capable-model` (or the
`WEBTEST_AGENT_CHEAP_MODEL` / `WEBTEST_AGENT_CAPABLE_MODEL` env vars).

## Backends

Two backends are supported natively, chosen with `--llm-provider` /
`WEBTEST_AGENT_LLM_PROVIDER` or auto-detected from credentials:

| Provider | Covers | Credentials |
|---|---|---|
| `anthropic` | Claude models via the Anthropic API | `ANTHROPIC_API_KEY` |
| `openai` | **any OpenAI-compatible endpoint** — OpenAI, Ollama, OpenRouter, Gemini, vLLM, LM Studio, Groq, Together, LiteLLM proxy, ... | `OPENAI_API_KEY` and/or `OPENAI_BASE_URL` |

**Auto-detection:** `ANTHROPIC_API_KEY` set → `anthropic`. Otherwise
`OPENAI_API_KEY` or `OPENAI_BASE_URL` set → `openai`. Neither → heuristic mode
(see below). `--dry-run` always shows what resolved.

## Setup by provider

=== "Anthropic (default)"

    ```bash
    export ANTHROPIC_API_KEY=sk-ant-...
    Anjalikastra https://example.com
    ```

    Any Claude model ID your key can access works for either tier.

=== "OpenAI"

    ```bash
    export OPENAI_API_KEY=sk-...
    Anjalikastra https://example.com \
      --cheap-model gpt-5-mini --capable-model gpt-5
    ```

=== "Ollama (local)"

    No API key needed — setting the base URL alone selects the `openai` backend:

    ```bash
    export OPENAI_BASE_URL=http://localhost:11434/v1
    Anjalikastra https://example.com \
      --cheap-model llama3.2 --capable-model qwen2.5-coder:32b
    ```

=== "OpenRouter"

    One key, hundreds of models across providers:

    ```bash
    export OPENAI_BASE_URL=https://openrouter.ai/api/v1
    export OPENAI_API_KEY=sk-or-...
    Anjalikastra https://example.com \
      --cheap-model google/gemini-2.5-flash \
      --capable-model anthropic/claude-sonnet-4.5
    ```

=== "Gemini"

    Via Google's OpenAI-compatible endpoint:

    ```bash
    export OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
    export OPENAI_API_KEY=your-gemini-api-key
    Anjalikastra https://example.com \
      --cheap-model gemini-2.5-flash --capable-model gemini-2.5-pro
    ```

=== "Anything else"

    Any server speaking the OpenAI Chat Completions protocol works the same way —
    vLLM, LM Studio, Groq, Together, a LiteLLM proxy:

    ```bash
    export OPENAI_BASE_URL=http://your-server:port/v1
    export OPENAI_API_KEY=key-if-your-server-checks-one
    Anjalikastra https://example.com --cheap-model <name> --capable-model <name>
    ```

> [!WARNING]
> **Model names must match your endpoint**
> When using a non-Anthropic provider, pass model names your endpoint actually
> serves. The CLI warns if you select `openai` but leave the Claude defaults
> in place.

## No key at all: heuristic mode

Without any LLM configured, the tool still runs end-to-end:

- Classification falls back to URL-pattern and DOM heuristics.
- Generation uses the deterministic templates only (they always produce a valid,
  runnable suite — the LLM's role is enrichment, not correctness).
- Triage marks failures `needs_human_review` rather than guessing.

The result is smaller and less targeted, but never broken.

## Resilience and cost accounting

- A failed LLM call (network error, rate limit, bad response) degrades **that
  one item** to its heuristic fallback — it never crashes the run.
- Every call logs a token-usage line, and the report's Cost section records the
  provider, per-tier call counts, token totals, and cache hit rate.
