"""BFS crawl from seed URLs, respecting robots.txt and a per-request throttle.

Uses a plain HTTP client (not a browser) for speed; endpoints.py separately drives
a real browser to capture the JS-rendered network surface. Pages that only exist
behind client-side rendering may be missed here — that gap is surfaced honestly in
the coverage report (Phase 7), not hidden.
"""

from __future__ import annotations

import asyncio
import logging
import time
import urllib.robotparser as robotparser
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urldefrag, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("anjalikastra.discovery.crawler")

_SKIP_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".css", ".js", ".mjs", ".json", ".xml",
    ".pdf", ".zip", ".tar", ".gz", ".mp4", ".mp3", ".woff", ".woff2", ".ttf",
)


@dataclass
class PageRecord:
    url: str
    status: int | None
    load_time_ms: float | None
    source: str  # "sitemap", "crawl", or "sitemap+crawl"
    error: str | None = None
    content_type: str | None = None


@dataclass
class CrawlResult:
    pages: list[PageRecord] = field(default_factory=list)
    blocked_by_robots: list[str] = field(default_factory=list)
    truncated: bool = False  # hit max_pages before exhausting the frontier
    unreached_sitemap_urls: list[str] = field(default_factory=list)  # listed in sitemap, never fetched
    html_by_url: dict[str, str] = field(default_factory=dict)  # 200 HTML pages, reused by analysis/generation

    def to_dict(self) -> dict[str, Any]:
        return {
            "pages": [asdict(p) for p in self.pages],
            "blocked_by_robots": self.blocked_by_robots,
            "truncated": self.truncated,
            "unreached_sitemap_urls": self.unreached_sitemap_urls,
            "html_by_url": self.html_by_url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CrawlResult":
        return cls(
            pages=[PageRecord(**p) for p in data["pages"]],
            blocked_by_robots=data["blocked_by_robots"],
            truncated=data["truncated"],
            unreached_sitemap_urls=data["unreached_sitemap_urls"],
            html_by_url=data["html_by_url"],
        )


class Throttle:
    """Enforces a minimum delay between consecutive requests.

    A crawler hammering every URL on a site can look like a denial-of-service
    attack against the user's own infrastructure — this is a hard floor, not a
    suggestion, and applies even if callers race each other.
    """

    def __init__(self, min_interval_ms: int):
        self._min_interval = min_interval_ms / 1000
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_request = time.monotonic()


class Robots:
    def __init__(self, enabled: bool):
        self._enabled = enabled
        self._parser: robotparser.RobotFileParser | None = None

    async def load(self, base_url: str, client: httpx.AsyncClient) -> None:
        if not self._enabled:
            return
        robots_url = urljoin(base_url, "/robots.txt")
        try:
            resp = await client.get(robots_url, timeout=10)
            parser = robotparser.RobotFileParser()
            if resp.status_code == 200:
                parser.parse(resp.text.splitlines())
            else:
                parser.parse([])  # no robots.txt => allow all
            self._parser = parser
        except httpx.HTTPError as exc:
            logger.debug("robots.txt fetch failed: %s — allowing all by default", exc)
            self._parser = None

    def allowed(self, url: str, user_agent: str = "Anjalikastra") -> bool:
        if not self._enabled or self._parser is None:
            return True
        return self._parser.can_fetch(user_agent, url)


def _normalize(url: str) -> str:
    url, _frag = urldefrag(url)
    parsed = urlparse(url)
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return parsed._replace(path=path).geturl()


def _same_origin(url: str, origin: str) -> bool:
    a, b = urlparse(url), urlparse(origin)
    return (a.scheme, a.netloc) == (b.scheme, b.netloc)


def _extract_links(html: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absolute = urljoin(page_url, href)
        if absolute.lower().endswith(_SKIP_EXTENSIONS):
            continue
        links.append(_normalize(absolute))
    return links


async def crawl(
    base_url: str,
    seeds: list[str],
    max_pages: int,
    throttle_ms: int,
    respect_robots: bool,
    client: httpx.AsyncClient,
) -> CrawlResult:
    origin = base_url
    throttle = Throttle(throttle_ms)
    robots = Robots(respect_robots)
    await robots.load(base_url, client)

    frontier: list[str] = [_normalize(base_url)] + [_normalize(u) for u in seeds if _same_origin(u, origin)]
    frontier_seen: set[str] = set()
    sitemap_urls = {_normalize(u) for u in seeds}

    result = CrawlResult()
    visited: dict[str, PageRecord] = {}
    html_by_url: dict[str, str] = {}
    queue: list[str] = []
    for url in frontier:
        if url not in frontier_seen:
            frontier_seen.add(url)
            queue.append(url)

    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        if not robots.allowed(url):
            result.blocked_by_robots.append(url)
            continue

        await throttle.wait()
        start = time.monotonic()
        try:
            resp = await client.get(url, timeout=15, follow_redirects=True)
            elapsed_ms = (time.monotonic() - start) * 1000
            final_url = _normalize(str(resp.url))
            source = "sitemap+crawl" if url in sitemap_urls else "crawl"
            record = PageRecord(
                url=final_url,
                status=resp.status_code,
                load_time_ms=round(elapsed_ms, 1),
                source=source,
                content_type=resp.headers.get("content-type"),
            )
            visited[final_url] = record

            is_html = (resp.headers.get("content-type") or "").startswith("text/html")
            if resp.status_code == 200 and is_html:
                html_by_url[final_url] = resp.text
                for link in _extract_links(resp.text, final_url):
                    if link not in visited and link not in frontier_seen and _same_origin(link, origin):
                        frontier_seen.add(link)
                        queue.append(link)
        except httpx.HTTPError as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            visited[url] = PageRecord(
                url=url, status=None, load_time_ms=round(elapsed_ms, 1), source="crawl", error=str(exc)
            )

    result.unreached_sitemap_urls = sorted(seed for seed in sitemap_urls if seed not in visited)
    result.truncated = bool(queue) and len(visited) >= max_pages
    result.pages = list(visited.values())
    result.html_by_url = html_by_url
    logger.info("crawl: visited %d pages (truncated=%s)", len(result.pages), result.truncated)
    return result
