# FAQ

## The crawler reaches zero pages. What's wrong?

Most often the site's bot protection (Cloudflare, WAF rules, ...) is blocking
the crawler. webtest-agent **never attempts to evade bot detection** — the
supported fix is to allowlist the tool's User-Agent on your own infrastructure:

```
webtest-agent/0.1 (+https://github.com/webtest-agent/webtest-agent)
```

The CLI prints this exact guidance when a crawl comes back empty.

## Why aren't my login-gated pages tested?

v1 crawls **public pages only**. Auth-gated areas show up in the coverage
report as *not reached* — deliberately, because silently skipping them (or
pretending they passed) would be worse than saying "not covered."
Authenticated crawling via stored session state or a scripted login step is the
designed v2 feature; see `webtest_agent/discovery/auth.py`.

## Are these unit tests?

No — and the tool never calls them that. Unit tests require source access.
webtest-agent produces **end-to-end / functional / smoke tests** that drive a
real browser against the live site.

## Do I need an LLM API key?

No. Without one the tool runs in heuristic/template-only mode: URL/DOM
heuristics classify pages, and the deterministic templates generate the suite.
It's smaller and less targeted than an LLM-assisted run, but always valid and
runnable. With a key (Anthropic, or anything OpenAI-compatible — see
[LLM Providers](providers.md)) you get better-targeted assertions and smarter
failure triage.

## A generated test fails — is that a bug in my site?

Maybe. Triage classifies each failure as regression / flake / expected-change /
needs-human-review, with a confidence score and reasoning in the report. A site
that changed since generation commonly produces *expected-change* failures —
re-run webtest-agent to regenerate against the current site, or just edit the
test (it's plain Playwright).

## Can I run this against a site I don't own?

Only with authorization. The tool is deliberately polite — throttled, robots.txt
respected, no evasion — but E2E-testing infrastructure you don't control isn't
what it's for. Test your own sites, staging environments, or targets you're
explicitly authorized to test.

## Does it file bugs or fix anything automatically?

No. Autonomy ends at "produce a report + suite." Drafted bugs are queued in the
report for a human to review; nothing touches an issue tracker, and nothing is
auto-fixed.

## Is my crawl data sent anywhere?

Page excerpts (a few KB of HTML per page) and endpoint samples are sent to
**your configured LLM provider** for classification and generation — that's the
only external destination. Use Ollama with a local model if the content must
never leave your machine. With no LLM configured, nothing leaves your machine
at all except the crawl of the target itself.
