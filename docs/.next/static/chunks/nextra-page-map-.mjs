export const pageMap = [{
  name: "docs",
  route: "/docs",
  children: [{
    name: "_index",
    route: "/docs/_index",
    frontMatter: {
      "linkTitle": "Documentation",
      "title": "Introduction"
    }
  }, {
    name: "caching-resuming",
    route: "/docs/caching-resuming",
    frontMatter: {
      "title": "Caching & Resuming",
      "weight": 6
    }
  }, {
    name: "cli",
    route: "/docs/cli",
    frontMatter: {
      "title": "CLI Reference",
      "weight": 2
    }
  }, {
    name: "contributing",
    route: "/docs/contributing",
    frontMatter: {
      "title": "Contributing",
      "weight": 8
    }
  }, {
    name: "faq",
    route: "/docs/faq",
    frontMatter: {
      "title": "FAQ",
      "weight": 7
    }
  }, {
    name: "getting-started",
    route: "/docs/getting-started",
    frontMatter: {
      "title": "Getting Started",
      "weight": 1
    }
  }, {
    name: "how-it-works",
    route: "/docs/how-it-works",
    frontMatter: {
      "title": "How It Works",
      "weight": 4
    }
  }, {
    name: "output",
    route: "/docs/output",
    frontMatter: {
      "title": "Reports & Generated Suite",
      "weight": 5
    }
  }, {
    name: "providers",
    route: "/docs/providers",
    frontMatter: {
      "title": "LLM Providers",
      "weight": 3
    }
  }]
}, {
  name: "index",
  route: "/",
  frontMatter: {
    "sidebarTitle": "Index"
  }
}];