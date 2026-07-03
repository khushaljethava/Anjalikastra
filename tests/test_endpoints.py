from anjalikastra.discovery.endpoints import EndpointRecord, _path_pattern, merge_endpoints


def test_path_pattern_collapses_numeric_ids():
    assert _path_pattern("http://h/products/1") == "/products/:id"
    assert _path_pattern("http://h/products/42") == "/products/:id"


def test_path_pattern_collapses_uuids():
    assert _path_pattern("http://h/orders/550e8400-e29b-41d4-a716-446655440000") == "/orders/:id"


def test_path_pattern_leaves_static_segments_alone():
    assert _path_pattern("http://h/api/products") == "/api/products"


def test_merge_endpoints_prefers_observed_and_dedupes():
    observed = [EndpointRecord(method="GET", path_pattern="/api/products/:id", statuses=[200])]
    documented = [
        EndpointRecord(method="GET", path_pattern="/api/products/:id", from_openapi=True),
        EndpointRecord(method="POST", path_pattern="/api/products", from_openapi=True),
    ]
    merged = merge_endpoints(observed, documented)
    assert len(merged) == 2
    get_products_id = next(e for e in merged if e.path_pattern == "/api/products/:id")
    assert get_products_id.statuses == [200]  # kept the observed record, not the documented stub
