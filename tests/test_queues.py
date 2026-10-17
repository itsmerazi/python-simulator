from engine.queues import make_queue, put_wait, RateLimiter

def test_full_queue_refuses():
    q = make_queue(1)
    assert put_wait(q, "a", 0.01)
    assert not put_wait(q, "b", 0.01)
    assert q.qsize() == 1

def test_limiter_caps_rate():
    limiter = RateLimiter(30)
    assert limiter.allow()
    assert not limiter.allow()  # a second call within 33 ms is refused