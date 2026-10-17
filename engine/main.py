import queue
import threading

from . import mqtt_io
from .config import Q1_SIZE, Q2_SIZE, load_settings
from .jsonlog import log
from .queues import make_queue

def main():
    s = load_settings()
    q1 = make_queue(Q1_SIZE) # inbound: ingress callback -> engine loop
    q2 = make_queue(Q2_SIZE) # outbound: engine loop -> egress thread
    stop = threading.Event()
    conn = mqtt_io.connect(s)
    mqtt_io.subscribe_commands(conn, q1)
    threading.Thread(target=mqtt_io.egress_loop, args=(conn, q2, stop),
    name="egress", daemon=True).start()
    log("engine_started", client_id=s.client_id)
    try:
        while not stop.is_set():
            try:
                client_id, raw, t_in = q1.get(timeout=0.5)
            except queue.Empty:
                continue
            log("q1_received", client_id=client_id, bytes=len(raw))
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        conn.disconnect().result()
        log("engine_stopped")

if __name__ == "__main__":
    main()