import time

import httpx
import pytest

from webtest_agent.discovery.crawler import Throttle, _normalize, crawl
from webtest_agent.discovery.sitemap import fetch_sitemap_urls


def test_normalize_dedupes_root_with_and_without_trailing_slash():
    assert _normalize("http://host:1/") == _normalize("http://host:1")


def test_normalize_strips_trailing_slash_on_subpaths():
    assert _normalize("http://host/about/") == "http://host/about"


async def test_crawl_finds_pages_and_dedupes(fixture_site):
    async with httpx.AsyncClient() as client:
        seeds = await fetch_sitemap_urls(fixture_site.base_url, client)
        result = await crawl(fixture_site.base_url, seeds, max_pages=30, throttle_ms=1, respect_robots=True, client=client)

    urls = {p.url for p in result.pages}
    assert len(urls) == len(result.pages)  # no duplicates
    assert any(u.endswith("/about") for u in urls)
    assert any(u.endswith("/login") for u in urls)
    statuses = {p.url: p.status for p in result.pages}
    assert all(s is not None for s in statuses.values())


async def test_crawl_respects_max_pages(fixture_site):
    async with httpx.AsyncClient() as client:
        result = await crawl(fixture_site.base_url, [], max_pages=2, throttle_ms=1, respect_robots=True, client=client)
    assert len(result.pages) <= 2


async def test_throttle_enforces_minimum_interval():
    throttle = Throttle(min_interval_ms=100)
    start = time.monotonic()
    await throttle.wait()
    await throttle.wait()
    await throttle.wait()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.2  # two waits of >=100ms each after the first
