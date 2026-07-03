from webtest_agent.generation.assertions import EndpointAssertions, FormInfo, PageAssertions
from webtest_agent.generation.codegen import (
    generate_endpoint_files,
    generate_page_file,
    generate_page_spec_deterministic,
)
from webtest_agent.generation.review_gate import review_file
from webtest_agent.llm.client import LLMClient


def _page_assertions(**overrides) -> PageAssertions:
    defaults = dict(
        url="http://h/about",
        page_type="article",
        title="About",
        expected_status_ok=True,
        has_nav=True,
        h1_text="About us",
        forms=[],
        load_time_threshold_ms=5000,
        anomaly=None,
    )
    defaults.update(overrides)
    return PageAssertions(**defaults)


def test_deterministic_page_spec_passes_review_gate():
    content = generate_page_spec_deterministic(_page_assertions())
    result = review_file(content, "about.spec.ts")
    assert result.passed, result.violations


async def test_generate_page_file_falls_back_to_deterministic_without_llm():
    llm = LLMClient("cheap", "capable")
    gf = await generate_page_file(_page_assertions(), llm)
    assert gf.source == "deterministic"
    assert gf.review.passed


def test_generated_file_includes_form_required_field_assertions():
    form = FormInfo(action="/login", method="POST", required_fields=["email", "password"], has_password_field=True)
    assertions = _page_assertions(url="http://h/login", page_type="login", forms=[form])
    content = generate_page_spec_deterministic(assertions)
    assert "email" in content
    assert "password" in content
    assert "toHaveAttribute('required'" in content


async def test_generate_endpoint_files_groups_by_resource():
    assertions = [
        EndpointAssertions(method="GET", path_pattern="/api/products/:id", endpoint_type="read_detail",
                            expected_status=200, response_is_json=True, response_top_level_keys=["id", "name"],
                            negative_cases=["invalid_id"]),
    ]
    llm = LLMClient("cheap", "capable")
    files = await generate_endpoint_files(assertions, {"GET /api/products/:id": "http://h/api/products/1"}, llm)
    assert len(files) == 1
    assert files[0].review.passed
    assert "api/products/1" in files[0].content or "api/products/:id" in files[0].content
