"""F1-T10: feature computation stays under 1 ms per request on CPU."""

import time

from wafarena.features.request import RequestInput, request_features
from wafarena.features.session import SessionTracker

BUDGET_SECONDS = 1e-3
ITERATIONS = 2000
PAYLOAD = "' UNION SELECT username, password FROM users -- " * 3


def test_request_and_session_features_under_one_millisecond():
    tracker = SessionTracker()
    request = RequestInput(params={"q": PAYLOAD, "id": "1 OR 1=1"})
    for _ in range(4):
        tracker.record(request, modsec_pl2=0.3, allowed=False)

    start = time.perf_counter()
    for _ in range(ITERATIONS):
        request_features(request)
        tracker.session_features()
        tracker.window_features()
    elapsed = (time.perf_counter() - start) / ITERATIONS

    assert elapsed < BUDGET_SECONDS, f"{elapsed * 1e6:.1f} us per request"
