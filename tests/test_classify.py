from webtest_agent.analysis.classify import classify_endpoint, classify_page
from webtest_agent.cache.store import CacheStore
from webtest_agent.discovery.crawler import PageRecord
from webtest_agent.discovery.endpoints import EndpointRecord
from webtest_agent.llm.client import LLMClient


async def test_classify_page_heuristic_login(tmp_path):
    llm = LLMClient("cheap-model", "capable-model")  # no ANTHROPIC_API_KEY in test env
    cache = CacheStore(tmp_path / "cache")
    page = PageRecord(url="http://h/login", status=200, load_time_ms=10, source="crawl")
    html = '<html><body><form><input type="password"></form></body></html>'

    result = await classify_page(page, html, llm, cache)
    assert result.page_type == "login"
    assert not llm.available


async def test_classify_page_is_cached_by_content_hash(tmp_path):
    llm = LLMClient("cheap-model", "capable-model")
    cache = CacheStore(tmp_path / "cache")
    page = PageRecord(url="http://h/about", status=200, load_time_ms=10, source="crawl")
    html = "<html><body><h1>About</h1></body></html>"

    first = await classify_page(page, html, llm, cache)
    assert cache.stats.misses == 1
    second = await classify_page(page, html, llm, cache)
    assert cache.stats.hits == 1
    assert first.page_type == second.page_type


async def test_classify_endpoint_heuristic_mutation(tmp_path):
    llm = LLMClient("cheap-model", "capable-model")
    cache = CacheStore(tmp_path / "cache")
    ep = EndpointRecord(method="POST", path_pattern="/api/orders")
    result = await classify_endpoint(ep, llm, cache)
    assert result.endpoint_type == "mutation"
