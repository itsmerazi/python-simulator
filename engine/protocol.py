import time

from . import messages
from .messages import BadMessage

TTL_SECONDS = 60       # how long a correlation_id is remembered
REGISTRY_MAX = 10000   # hard cap: the registry is bounded, like the queues

class Protocol:
    # Used by the engine loop only, so it needs no lock.

    def __init__(self, core):
        self.core = core
        # (client_id, correlation_id) -> (expires_at, first audit record).
        # Keyed by both, so one client can never collide with another's IDs.
        self.seen = {}

    def handle(self, client_id, raw):
        # Returns (audit_record, change); change is None unless the command was applied.
        try:
            cmd = messages.parse_command(client_id, raw)  # check (2)
        except BadMessage as err:
            return messages.audit(client_id, None, "rejected", str(err)), None
        key = (client_id, cmd.correlation_id)
        self._expire()
        if key in self.seen:  # check (3)
            return dict(self.seen[key][1], status="duplicate"), None
        try:
            change = self.core.apply(cmd.payload)  # step (4)
            record = messages.audit(client_id, cmd.correlation_id, "accepted")
        except ValueError as err:
            change = None
            record = messages.audit(client_id, cmd.correlation_id, "rejected", str(err))
        self.seen[key] = (time.monotonic() + TTL_SECONDS, record)
        return record, change

    def _expire(self):
        # Entries are added in time order, so the oldest is always first:
        # drop expired entries from the front, and the oldest when at the cap.
        now = time.monotonic()
        while self.seen:
            oldest = next(iter(self.seen))
            if self.seen[oldest][0] > now and len(self.seen) < REGISTRY_MAX:
                break
            del self.seen[oldest]