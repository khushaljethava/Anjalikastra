"""Capture the API surface a site actually uses by watching XHR/fetch traffic
while the crawled pages load in a real browser, plus optional OpenAPI enrichment.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.async_api import Browser, Request, Response

logger = logging.getLogger("webtest_agent.discovery.endpoints")

_ID_SEGMENT = re.compile(
    r"^([0-9]+|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|[0-9a-fA-F]{24})$"
)
_SAMPLE_BYTES_CAP = 2000


@dataclass
class EndpointRecord:
    method: str
    path_pattern: str
    observed_urls: list[str] = field(default_factory=list)
    statuses: list[int] = field(default_factory=list)
    sample_request_body: str | None = None
    sample_response_body: str | None = None
    from_openapi: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EndpointRecord":
        return cls(**data)


def _path_pattern(url: str) -> str:
    """Collapse numeric/UUID/ObjectId path segments to :id so /users/42 and
    /users/91 merge into one endpoint record instead of one-per-instance."""
    parsed = urlparse(url)
    segments = [seg if not _ID_SEGMENT.match(seg) else ":id" for seg in parsed.path.split("/")]
    return "/".join(segments) or "/"


async def capture_endpoints_for_pages(
    browser: Browser,
    page_urls: list[str],
    throttle: "object",  # discovery.crawler.Throttle — duck-typed to avoid a circular import
    timeout_ms: int = 15_000,
) -> list[EndpointRecord]:
    """Visit each page in a fresh browser context, recording XHR/fetch calls it fires."""
    endpoints: dict[tuple[str, str], EndpointRecord] = {}
    context = await browser.new_context()

    async def on_response(response: Response) -> None:
        request: Request = response.request
        if request.resource_type not in ("xhr", "fetch"):
            return
        key = (request.method, _path_pattern(request.url))
        record = endpoints.setdefault(key, EndpointRecord(method=request.method, path_pattern=key[1]))
        if request.url not in record.observed_urls:
            record.observed_urls.append(request.url)
        record.statuses.append(response.status)

        if record.sample_request_body is None:
            try:
                post_data = request.post_data
                if post_data:
                    record.sample_request_body = post_data[:_SAMPLE_BYTES_CAP]
            except Exception:  # noqa: BLE001 - best-effort sampling, never fatal
                pass
        if record.sample_response_body is None:
            try:
                body = await response.body()
                record.sample_response_body = body[:_SAMPLE_BYTES_CAP].decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001 - some responses (e.g. streamed) aren't readable
                pass

    page = await context.new_page()
    page.on("response", on_response)

    for url in page_urls:
        await throttle.wait()
        try:
            await page.goto(url, timeout=timeout_ms, wait_until="networkidle")
        except Exception as exc:  # noqa: BLE001 - navigation failures are recorded, not fatal
            logger.debug("endpoint capture: navigation failed for %s: %s", url, exc)

    await context.close()
    logger.info("endpoint capture: observed %d distinct endpoints", len(endpoints))
    return list(endpoints.values())


def load_openapi_endpoints(path: Path) -> list[EndpointRecord]:
    """Best-effort parse of an OpenAPI 3.x doc (JSON or YAML) into EndpointRecords.
    Never required — this only enriches, never gates, endpoint discovery."""
    text = path.read_text()
    if path.suffix.lower() in (".yaml", ".yml"):
        import yaml

        spec = yaml.safe_load(text)
    else:
        spec = json.loads(text)

    records: list[EndpointRecord] = []
    for path_str, methods in (spec.get("paths") or {}).items():
        for method, _operation in (methods or {}).items():
            if method.lower() not in ("get", "post", "put", "patch", "delete"):
                continue
            records.append(
                EndpointRecord(method=method.upper(), path_pattern=path_str, from_openapi=True)
            )
    logger.info("openapi: loaded %d documented endpoints from %s", len(records), path)
    return records


def merge_endpoints(observed: list[EndpointRecord], documented: list[EndpointRecord]) -> list[EndpointRecord]:
    """Dedupe by (method, path-pattern); prefer observed data but flag OpenAPI-only endpoints."""
    merged: dict[tuple[str, str], EndpointRecord] = {(e.method, e.path_pattern): e for e in observed}
    for doc in documented:
        key = (doc.method, doc.path_pattern)
        if key not in merged:
            merged[key] = doc
    return sorted(merged.values(), key=lambda e: (e.path_pattern, e.method))
