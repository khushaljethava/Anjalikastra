---
title: FAQ
description: Common questions about Anjalikastra — crawler blocks, auth pages, LLM keys, and generated test failures.
sidebar:
  order: 7
---

## The crawler reaches zero pages. What's wrong?

Bot protection (Cloudflare, WAF) is likely blocking the crawler. Allowlist this User-Agent on your infrastructure:

```
Anjalikastra/0.1 (+https://github.com/khushaljethava/Anjalikastra)
```

## Why aren't login-gated pages tested?

v1 crawls **public pages only**. Auth-gated areas appear as *not reached* in the coverage report.

## Are these unit tests?

No. Anjalikastra produces **E2E / functional / smoke tests** against the live site. Unit tests require source access.

## Do I need an LLM API key?

No. Heuristic mode still produces a valid, runnable suite. With a key you get better assertions and smarter triage.

## A generated test fails — is that a bug in my site?

Maybe. Triage classifies failures with confidence scores. Site changes often produce *expected-change* failures — edit the test or re-run Anjalikastra.

## Can I run this against a site I don't own?

Only with authorization. Test your own sites, staging, or explicitly authorized targets.

## Does it file bugs automatically?

No. Drafted bugs are queued in the report for human review.

## Is crawl data sent anywhere?

Page excerpts go to **your configured LLM provider** only. Use Ollama locally or run without an LLM to keep data on your machine.
