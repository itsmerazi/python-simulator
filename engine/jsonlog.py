import json
import threading
import time

_lock = threading.Lock()

def log(event, **fields):
    record = {"ts": round(time.time(), 3), "event": event}
    record.update(fields)
    line = json.dumps(record, separators=(",", ":"))
    with _lock:
        print(line, flush=True)