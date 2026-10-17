import queue
import time

def make_queue(size):
    return queue.Queue(maxsize=size)

def put_wait(q, item, timeout):
    # Backpressure: wait a little for space, then give up instead of growing.
    try:
        q.put(item, timeout=timeout)
        return True
    except queue.Full:
        return False
class RateLimiter:
    # Used by one thread only (the engine loop), so it needs no lock.
    def __init__(self, hz):
        self.interval = 1.0 / hz
        self.next_ok = 0.0

    def allow(self):
        now = time.monotonic() # monotonic clock, not the wall clock
        if now >= self.next_ok:
            self.next_ok = now + self.interval
            return True
        return False

def offer_telemetry(q2, limiter, item):
    # Returns False when the limiter or a full Q2 refuses the snapshot.
    # The caller keeps the state marked as changed and offers a newer one later.
    if not limiter.allow():
        return False
    try:
        q2.put_nowait(item)
        return True
    except queue.Full:
        return False