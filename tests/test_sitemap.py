import httpx

from anjalikastra.discovery.sitemap import fetch_sitemap_urls


async def test_sitemap_parses_seed_urls(fixture_site):
    async with httpx.AsyncClient() as client:
        urls = await fetch_sitemap_urls(fixture_site.base_url, client)
    assert urls
    assert any(u.endswith("/about") for u in urls)


async def test_sitemap_missing_returns_empty_list_not_error():
    async with httpx.AsyncClient() as client:
        # nothing listening on this port
        urls = await fetch_sitemap_urls("http://127.0.0.1:1", client)
    assert urls == []
