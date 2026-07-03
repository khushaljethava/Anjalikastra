from rich.console import Console

from anjalikastra.checkpoint import Checkpoint
from anjalikastra.config import Config
from anjalikastra.discovery.crawler import crawl
from anjalikastra.discovery.sitemap import fetch_sitemap_urls
import httpx
import os
import pytest

from anjalikastra.orchestrator import run_pipeline

_CHROMIUM = os.environ.get("WEBTEST_AGENT_CHROMIUM_PATH")
pytestmark = pytest.mark.skipif(not _CHROMIUM, reason="set WEBTEST_AGENT_CHROMIUM_PATH to run resume tests")


def test_checkpoint_roundtrips_to_disk(tmp_path):
    cp = Checkpoint(tmp_path)
    assert not cp.has("discovery")
    cp.save("discovery", {"a": 1})

    cp2 = Checkpoint(tmp_path)
    assert cp2.has("discovery")
    assert cp2.get("discovery") == {"a": 1}


async def test_resume_skips_discovery_and_reuses_crawl_data(fixture_site, tmp_path):
    console = Console(quiet=True)
    cfg = Config(url=fixture_site.base_url, output_dir=tmp_path, run_id="fixed-run", max_pages=20, throttle_ms=10, dry_run=True)
    await run_pipeline(cfg, console)

    checkpoint = Checkpoint(cfg.run_dir)
    assert checkpoint.has("discovery")
    first_page_count = len(checkpoint.get("discovery")["crawl"]["pages"])
    assert first_page_count > 0

    # Resuming with the same run_id must not re-crawl: verify by making the fixture
    # unreachable and confirming the second run still succeeds using checkpointed data.
    cfg_resume = Config(url="http://127.0.0.1:1", output_dir=tmp_path, run_id="fixed-run", max_pages=20, throttle_ms=10, dry_run=True)
    exit_code = await run_pipeline(cfg_resume, console)

    assert exit_code == 0
    checkpoint_after = Checkpoint(cfg_resume.run_dir)
    assert len(checkpoint_after.get("discovery")["crawl"]["pages"]) == first_page_count
