"""Infer what 'correct' means for a page or endpoint, from its content and type.

Deterministic and cheap by design (no LLM call here) — this is structural analysis
of the DOM/response, not generation. codegen.py turns these into actual test code.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from webtest_agent.analysis.classify import EndpointClassification, PageClassification
from webtest_agent.discovery.crawler import PageRecord
from webtest_agent.discovery.endpoints import EndpointRecord


@dataclass
class FormInfo:
    action: str | None
    method: str
    required_fields: list[str] = field(default_factory=list)
    has_password_field: bool = False


@dataclass
class PageAssertions:
    url: str
    page_type: str
    title: str | None
    expected_status_ok: bool  # False when the page itself is an intentional error page
    has_nav: bool
    h1_text: str | None
    forms: list[FormInfo] = field(default_factory=list)
    load_time_threshold_ms: int = 5000
    anomaly: str | None = None  # e.g. "non-2xx status on a page not classified as error"


@dataclass
class EndpointAssertions:
    method: str
    path_pattern: str
    endpoint_type: str
    expected_status: int
    response_is_json: bool
    response_top_level_keys: list[str] = field(default_factory=list)
    negative_cases: list[str] = field(default_factory=list)


def infer_page_assertions(
    page: PageRecord, html: str, classification: PageClassification, load_time_threshold_ms: int
) -> PageAssertions:
    soup = BeautifulSoup(html or "", "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    h1 = soup.find("h1")
    h1_text = h1.get_text(strip=True) if h1 else None

    forms = [_extract_form(form) for form in soup.find_all("form")]

    is_error_page = classification.page_type == "error"
    status_ok = page.status is not None and 200 <= page.status < 400
    anomaly = None
    if not is_error_page and not status_ok:
        anomaly = f"non-2xx status ({page.status}) on a page not classified as an error page"

    return PageAssertions(
        url=page.url,
        page_type=classification.page_type,
        title=title,
        expected_status_ok=not is_error_page,
        has_nav=soup.find("nav") is not None,
        h1_text=h1_text,
        forms=forms,
        load_time_threshold_ms=load_time_threshold_ms,
        anomaly=anomaly,
    )


def _extract_form(form) -> FormInfo:
    required = [
        (inp.get("name") or inp.get("id") or inp.get("type", "field"))
        for inp in form.find_all(["input", "select", "textarea"])
        if inp.has_attr("required")
    ]
    has_password = form.find("input", {"type": "password"}) is not None
    return FormInfo(
        action=form.get("action"),
        method=(form.get("method") or "GET").upper(),
        required_fields=required,
        has_password_field=has_password,
    )


def infer_endpoint_assertions(endpoint: EndpointRecord, classification: EndpointClassification) -> EndpointAssertions:
    statuses = endpoint.statuses or [200]
    expected_status = max(set(statuses), key=statuses.count)  # most common observed status

    response_is_json = False
    top_level_keys: list[str] = []
    if endpoint.sample_response_body:
        try:
            parsed = json.loads(endpoint.sample_response_body)
            response_is_json = True
            if isinstance(parsed, dict):
                top_level_keys = list(parsed.keys())[:10]
        except (json.JSONDecodeError, ValueError):
            pass

    negative_cases: list[str] = []
    if classification.endpoint_type == "mutation":
        negative_cases.append("missing_auth")
    if classification.endpoint_type in ("read_detail",) and ":id" in endpoint.path_pattern:
        negative_cases.append("invalid_id")
    if classification.endpoint_type == "auth":
        negative_cases.append("invalid_credentials")

    return EndpointAssertions(
        method=endpoint.method,
        path_pattern=endpoint.path_pattern,
        endpoint_type=classification.endpoint_type,
        expected_status=expected_status,
        response_is_json=response_is_json,
        response_top_level_keys=top_level_keys,
        negative_cases=negative_cases,
    )


def slugify(url_or_path: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", url_or_path).strip("-").lower()
    return slug or "root"
