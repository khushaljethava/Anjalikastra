---
title: LLM Providers
description: Configure Claude, OpenAI, Ollama, OpenRouter, Gemini, or run without an API key in heuristic mode.
sidebar:
  order: 3
---

Anjalikastra splits LLM work across two tiers so routine work stays cheap:

| Tier | Used for | Default model |
|---|---|---|
| **cheap** | page/endpoint classification, summaries | `claude-haiku-4-5-20251001` |
| **capable** | test generation, failure triage | `claude-sonnet-5` |

Override with `--cheap-model` / `--capable-model` or env vars
`WEBTEST_AGENT_CHEAP_MODEL` / `ANJALIKASTRA_CAPABLE_MODEL`.

## Backends

| Provider | Covers | Credentials |
|---|---|---|
| `anthropic` | Claude via Anthropic API | `ANTHROPIC_API_KEY` |
| `openai` | Any OpenAI-compatible endpoint | `OPENAI_API_KEY` and/or `OPENAI_BASE_URL` |

**Auto-detection:** `ANTHROPIC_API_KEY` → `anthropic`. Otherwise
`OPENAI_API_KEY` or `OPENAI_BASE_URL` → `openai`. Neither → heuristic mode.

## Setup examples

**Anthropic (default)**

```bash
export ANTHROPIC_API_KEY=sk-ant-...
anjalikastra https://example.com
```

**OpenAI**

```bash
export OPENAI_API_KEY=sk-...
anjalikastra https://example.com --cheap-model gpt-5-mini --capable-model gpt-5
```

**Ollama (local, no key)**

```bash
export OPENAI_BASE_URL=http://localhost:11434/v1
anjalikastra https://example.com --cheap-model llama3.2 --capable-model qwen2.5-coder:32b
```

**OpenRouter**

```bash
export OPENAI_BASE_URL=https://openrouter.ai/api/v1
export OPENAI_API_KEY=sk-or-...
anjalikastra https://example.com \
  --cheap-model google/gemini-2.5-flash \
  --capable-model anthropic/claude-sonnet-4.5
```

**Gemini**

```bash
export OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
export OPENAI_API_KEY=your-gemini-api-key
anjalikastra https://example.com --cheap-model gemini-2.5-flash --capable-model gemini-2.5-pro
```

> [!WARNING]
> When using a non-Anthropic provider, pass model names your endpoint actually serves.

## No key: heuristic mode

Without any LLM configured, the tool still runs end-to-end:

- Classification uses URL/DOM heuristics.
- Generation uses deterministic templates (always valid and runnable).
- Triage marks failures `needs_human_review` rather than guessing.

## Cost accounting

Failed LLM calls degrade that one item to heuristic fallback — never crashing the run.
The report's Cost section records provider, per-tier calls, tokens, and cache hit rate.
