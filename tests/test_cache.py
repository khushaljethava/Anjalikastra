from anjalikastra.cache.store import CacheStore, content_hash


def test_cache_hit_requires_matching_hash(tmp_path):
    store = CacheStore(tmp_path)
    store.set("ns", "key1", "hash-a", {"v": 1})

    assert store.get("ns", "key1", "hash-a") == {"v": 1}
    assert store.get("ns", "key1", "hash-b") is None  # content changed, cache must miss


def test_cache_persists_across_instances(tmp_path):
    store1 = CacheStore(tmp_path)
    store1.set("ns", "key1", "hash-a", {"v": 1})
    store1.flush()

    store2 = CacheStore(tmp_path)
    assert store2.get("ns", "key1", "hash-a") == {"v": 1}


def test_content_hash_stable_and_sensitive_to_change():
    assert content_hash("abc") == content_hash("abc")
    assert content_hash("abc") != content_hash("abd")
