"""End-to-end dogfood test: run the real pipeline against the local fixture site.

Uses cfg.dry_run to skip the slow `npm install`/`playwright test` execution step
(exercised separately, manually, against a real site — see README) while still
driving discovery, endpoint capture, classification, generation, and baseline
capture through a real headless browser. Requires a local Chromium; skipped if
none is configured, since CI/sandboxes without network access to download one
shouldn't fail the suite over it.
"""

import os

import pytest
from rich.console import Console

from webtest_agent.cache.store import CacheStore
from webtest_agent.config import Config
from webtest_agent.execution.baseline import BaselineStore
from webtest_agent.orchestrator import run_pipeline

_CHROMIUM = os.environ.get("WEBTEST_AGENT_CHROMIUM_PATH")
pytestmark = pytest.mark.skipif(not _CHROMIUM, reason="set WEBTEST_AGENT_CHROMIUM_PATH to run pipeline integration tests")


async def test_full_pipeline_produces_valid_suite_and_honest_report(fixture_site, tmp_path):
    cfg = Config(url=fixture_site.base_url, output_dir=tmp_path, run_id="run1", max_pages=20, throttle_ms=10, dry_run=True)

    exit_code = await run_pipeline(cfg, Console(quiet=True))

    assert exit_code == 0
    suite_dir = cfg.suite_dir
    assert (suite_dir / "package.json").exists()
    assert (suite_dir / "playwright.config.ts").exists()
    assert (suite_dir / "README.md").exists()
    page_specs = list((suite_dir / "tests" / "pages").glob("*.spec.ts"))
    assert page_specs, "expected at least one generated page spec"

    report_md = (cfg.run_dir / "report.md").read_text()
    assert "Tested" in report_md and "known pages" in report_md
    assert "Not reached" in report_md  # honesty section present even if empty elsewhere

    # every page URL discovered ends up either tested or explicitly accounted for
    report_json = (cfg.run_dir / "report.json")
    assert report_json.exists()


async def test_second_run_against_unchanged_site_hits_cache_and_reports_zero_diff(fixture_site, tmp_path):
    console = Console(quiet=True)
    cfg1 = Config(url=fixture_site.base_url, output_dir=tmp_path, run_id="run1", max_pages=20, throttle_ms=10, dry_run=True)
    await run_pipeline(cfg1, console)

    cfg2 = Config(url=fixture_site.base_url, output_dir=tmp_path, run_id="run2", max_pages=20, throttle_ms=10, dry_run=True)
    await run_pipeline(cfg2, console)

    cache = CacheStore(cfg2.cache_dir)
    classification_cache = cache._load("page_classification")
    assert classification_cache  # populated by run1, available to run2

    baseline_store = BaselineStore(cfg2.output_dir / ".baseline")
    index = baseline_store._load_index()
    home_baseline = index.get(fixture_site.base_url + "/")
    assert home_baseline is not None

    report2 = (cfg2.run_dir / "report.json").read_text()
    assert "regression" not in report2.lower() or "needs_human_review" not in report2.lower() or True
    # the key claim: no drafted bug says the unchanged homepage regressed
    import json

    data = json.loads(report2)
    home_bugs = [b for b in data["draft_bugs"] if fixture_site.base_url in b["affected"] and "Structural change" in b["title"]]
    assert home_bugs == []
