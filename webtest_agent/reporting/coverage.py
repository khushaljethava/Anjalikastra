"""Coverage accounting. Coverage honesty is mandatory: this module's job is to make
sure 'tested N of M known pages' always lists what wasn't reached, and why — never
a bare green checkmark that implies full coverage.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from webtest_agent.discovery.crawler import CrawlResult


@dataclass
class UnreachedPage:
    url: str
    reason: str


@dataclass
class CoverageSummary:
    known_pages: int
    tested_pages: int
    unreached: list[UnreachedPage] = field(default_factory=list)
    truncated: bool = False
    public_only: bool = True

    @property
    def coverage_percent(self) -> float:
        if self.known_pages == 0:
            return 0.0
        return round(100 * self.tested_pages / self.known_pages, 1)


def build_coverage(crawl: CrawlResult, tested_urls: set[str], public_only: bool) -> CoverageSummary:
    unreached: list[UnreachedPage] = []

    for url in crawl.unreached_sitemap_urls:
        unreached.append(UnreachedPage(url=url, reason="listed in sitemap.xml but never fetched (max-pages cap or unreachable)"))

    for url in crawl.blocked_by_robots:
        unreached.append(UnreachedPage(url=url, reason="disallowed by robots.txt"))

    for page in crawl.pages:
        if page.url not in tested_urls:
            if page.error:
                reason = f"fetch failed: {page.error}"
            elif page.status is None or page.status >= 400:
                reason = f"returned HTTP {page.status}"
            else:
                reason = "not generated into the suite"
            unreached.append(UnreachedPage(url=page.url, reason=reason))

    known = len(crawl.pages) + len(crawl.unreached_sitemap_urls) + len(crawl.blocked_by_robots)
    tested = len(tested_urls)

    return CoverageSummary(
        known_pages=known,
        tested_pages=tested,
        unreached=unreached,
        truncated=crawl.truncated,
        public_only=public_only,
    )
