from anjalikastra.analysis.classify import PageClassification
from anjalikastra.discovery.crawler import PageRecord
from anjalikastra.generation.assertions import infer_page_assertions, slugify


def test_infer_page_assertions_extracts_forms_and_required_fields():
    page = PageRecord(url="http://h/login", status=200, load_time_ms=10, source="crawl")
    html = """<html><head><title>Login</title></head><body>
        <nav></nav><h1>Log in</h1>
        <form><input name="email" required><input name="password" type="password" required></form>
    </body></html>"""
    classification = PageClassification(url=page.url, page_type="login", confidence=0.9)

    assertions = infer_page_assertions(page, html, classification, load_time_threshold_ms=5000)

    assert assertions.title == "Login"
    assert assertions.has_nav is True
    assert assertions.h1_text == "Log in"
    assert len(assertions.forms) == 1
    assert set(assertions.forms[0].required_fields) == {"email", "password"}
    assert assertions.forms[0].has_password_field is True
    assert assertions.expected_status_ok is True
    assert assertions.anomaly is None


def test_infer_page_assertions_flags_anomaly_on_unexpected_error_status():
    page = PageRecord(url="http://h/broken", status=500, load_time_ms=10, source="crawl")
    classification = PageClassification(url=page.url, page_type="article", confidence=0.5)
    assertions = infer_page_assertions(page, "<html></html>", classification, load_time_threshold_ms=5000)
    assert assertions.anomaly is not None


def test_infer_page_assertions_no_anomaly_for_intentional_error_page():
    page = PageRecord(url="http://h/404", status=404, load_time_ms=10, source="crawl")
    classification = PageClassification(url=page.url, page_type="error", confidence=0.9)
    assertions = infer_page_assertions(page, "<html></html>", classification, load_time_threshold_ms=5000)
    assert assertions.anomaly is None
    assert assertions.expected_status_ok is False


def test_slugify():
    assert slugify("/products/1") == "products-1"
    assert slugify("/") == "root"
