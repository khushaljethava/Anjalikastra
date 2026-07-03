"""Fetch and parse sitemap.xml (and sitemap index files).

Sitemaps are a seed list, not ground truth: they're often stale, incomplete, or
absent. The crawler (crawler.py) is the source of truth for what's actually reachable.
"""

from __future__ import annotations

import logging
from urllib.parse import urljoin
from xml.etree import ElementTree

import httpx

logger = logging.getLogger("anjalikastra.discovery.sitemap")

_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
_COMMON_PATHS = ("/sitemap.xml", "/sitemap_index.xml")


async def fetch_sitemap_urls(base_url: str, client: httpx.AsyncClient, max_depth: int = 3) -> list[str]:
    """Return the deduped list of page URLs listed in the site's sitemap(s), if any."""
    seeds: list[str] = []
    for path in _COMMON_PATHS:
        candidate = urljoin(base_url, path)
        try:
            urls = await _fetch_and_parse(candidate, client, max_depth)
        except (httpx.HTTPError, ElementTree.ParseError) as exc:
            logger.debug("sitemap fetch failed for %s: %s", candidate, exc)
            continue
        if urls:
            seeds.extend(urls)
            break  # first sitemap that resolves is enough as a seed source
    deduped = list(dict.fromkeys(seeds))
    logger.info("sitemap: found %d seed URLs", len(deduped))
    return deduped


async def _fetch_and_parse(url: str, client: httpx.AsyncClient, depth_remaining: int) -> list[str]:
    if depth_remaining <= 0:
        return []
    resp = await client.get(url, timeout=10)
    if resp.status_code != 200 or not resp.content:
        return []

    root = ElementTree.fromstring(resp.content)
    tag = root.tag.rsplit("}", 1)[-1]

    if tag == "sitemapindex":
        urls: list[str] = []
        for sitemap in root.findall("sm:sitemap/sm:loc", _NS):
            if sitemap.text:
                urls.extend(await _fetch_and_parse(sitemap.text.strip(), client, depth_remaining - 1))
        return urls

    if tag == "urlset":
        return [loc.text.strip() for loc in root.findall("sm:url/sm:loc", _NS) if loc.text]

    return []
