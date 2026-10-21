"""F1-T11: the ModSecurity cache persists and keys by config version, PL and request."""

from wafarena.envs.backends.cache import ModSecCache, request_hash


def test_request_hash_is_stable_and_depends_on_request():
    assert request_hash("GET", "/search?q=a") == request_hash("GET", "/search?q=a")
    assert request_hash("GET", "/search?q=a") != request_hash("GET", "/search?q=b")


def test_put_then_get_returns_stored_value(tmp_path):
    cache = ModSecCache(tmp_path / "c.json")
    cache.put(1, "GET", "/search?q=a", score=5, block=True)

    assert cache.get(1, "GET", "/search?q=a") == (5, True)


def test_get_misses_for_unknown_request(tmp_path):
    cache = ModSecCache(tmp_path / "c.json")

    assert cache.get(1, "GET", "/unknown") is None


def test_flush_persists_across_instances(tmp_path):
    path = tmp_path / "c.json"
    first = ModSecCache(path)
    first.put(2, "GET", "/search?q=x", score=10, block=True)
    first.flush()

    assert ModSecCache(path).get(2, "GET", "/search?q=x") == (10, True)


def test_different_pl_is_a_different_key(tmp_path):
    cache = ModSecCache(tmp_path / "c.json")
    cache.put(1, "GET", "/search?q=a", 5, True)

    assert cache.get(2, "GET", "/search?q=a") is None
