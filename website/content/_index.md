---
title: 'Home'
type: landing

sections:
  - block: hero
    content:
      title: Point it at a URL. Get a runnable test suite.
      text: Anjalikastra crawls a live website black-box and generates a runnable Playwright E2E suite plus an honest coverage report — no source access needed. 🕸️
      primary_action:
        text: Get Started
        url: /docs/getting-started/
        icon: rocket-launch
      secondary_action:
        text: Read the docs
        url: /docs/
    design:
      spacing:
        padding: [0, 0, 0, 0]
        margin: [0, 0, 0, 0]
  - block: features
    id: features
    content:
      title: Features
      text: One command against a live URL. Two deliverables — a human-readable report and a test suite you keep.
      items:
        - name: Black-box crawling
          icon: magnifying-glass
          description: Discovers pages and API endpoints from the live site alone — sitemap, crawl, and network capture. No repo or CI access.
        - name: Runnable Playwright suite
          icon: bolt
          description: TypeScript + Playwright Test files, config, and manifest that install and run with a single command on first try.
        - name: Honest coverage
          icon: check-circle
          description: Every report states "tested N of M known pages" and lists what wasn't reached and why. No bare green checkmarks.
        - name: Any LLM provider
          icon: sparkles
          description: Claude, OpenAI, Ollama, OpenRouter, Gemini — or no key at all with the heuristic fallback mode.
        - name: Cheap re-runs
          icon: arrow-path
          description: Content-hash caching and checkpointed discovery mean a second run against an unchanged site costs almost nothing.
        - name: Human in the loop
          icon: user
          description: Bugs are drafted, never auto-filed. A review gate applies minimal-code discipline to every generated test.
  - block: cta-card
    content:
      title: Install from PyPI
      text: "`pip install anjalikastra` — then point it at your site."
      button:
        text: Get Started
        url: /docs/getting-started/
    design:
      card:
        css_class: "bg-primary-700"
        css_style: ""
---
