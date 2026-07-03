from anjalikastra.discovery.crawler import CrawlResult, PageRecord
from anjalikastra.reporting.coverage import build_coverage


def test_coverage_is_honest_about_unreached_pages():
    crawl = CrawlResult(
        pages=[
            PageRecord(url="http://h/", status=200, load_time_ms=1, source="crawl"),
            PageRecord(url="http://h/broken", status=500, load_time_ms=1, source="crawl"),
        ],
        blocked_by_robots=["http://h/admin"],
        unreached_sitemap_urls=["http://h/stale-sitemap-entry"],
    )
    coverage = build_coverage(crawl, tested_urls={"http://h/"}, public_only=True)

    assert coverage.known_pages == 4  # 2 crawled + 1 robots-blocked + 1 sitemap-only
    assert coverage.tested_pages == 1
    assert coverage.coverage_percent == 25.0
    reasons = {u.url: u.reason for u in coverage.unreached}
    assert "robots.txt" in reasons["http://h/admin"]
    assert "sitemap.xml" in reasons["http://h/stale-sitemap-entry"]
    assert "500" in reasons["http://h/broken"]


def test_coverage_never_silently_implies_full_coverage_when_nothing_tested():
    crawl = CrawlResult(pages=[PageRecord(url="http://h/", status=200, load_time_ms=1, source="crawl")])
    coverage = build_coverage(crawl, tested_urls=set(), public_only=True)
    assert coverage.coverage_percent == 0.0
    assert len(coverage.unreached) == 1
