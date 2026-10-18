import queue
import signal
import threading
import time

from . import mqtt_io
from .config import Q1_SIZE, Q2_SIZE, TICK_HZ, load_settings
from .jsonlog import log
from .messages import encode, telemetry
from .protocol import Protocol
from .queues import RateLimiter, make_queue, offer_telemetry, put_wait
from .simulation_core import SimulationCore

DT = 1.0 / TICK_HZ

def main():
    s = load_settings()
    q1 = make_queue(Q1_SIZE)  # inbound: ingress callback -> engine loop
    q2 = make_queue(Q2_SIZE)  # outbound: engine loop -> egress thread
    stop = threading.Event()
    # docker stop sends SIGTERM: turn it into a clean stop.
    signal.signal(signal.SIGTERM, lambda signum, frame: stop.set())

    core = SimulationCore()
    protocol = Protocol(core)
    limiter = RateLimiter(s.telemetry_hz)

    conn = mqtt_io.connect(s)
    mqtt_io.subscribe_commands(conn, q1)
    threading.Thread(target=mqtt_io.egress_loop, args=(conn, q2, stop),
                     name="egress", daemon=True).start()
    log("engine_started", client_id=s.client_id, tick_hz=TICK_HZ,
        telemetry_hz=s.telemetry_hz)

    dirty = False    # the state changed since the last snapshot was sent
    last_cid = None  # newest command that changed the state, not yet sent
    seq = 0
    next_tick = time.monotonic()
    try:
        while not stop.is_set():
            wait = next_tick - time.monotonic()
            if wait > 0:
                # Between ticks: handle commands until the next tick is due.
                try:
                    client_id, raw, t_in = q1.get(timeout=wait)
                except queue.Empty:
                    continue
                record, change = protocol.handle(client_id, raw)
                put_wait(q2, ("simulation/audit/" + client_id, encode(record), 1), 1.0)
                log("audit", tick=core.ticks, change=change,
                    handle_ms=round((time.monotonic() - t_in) * 1000, 3), **record)
                if change:
                    dirty, last_cid = True, record["correlation_id"]
                continue

            # A tick is due: advance the robot by one fixed step.
            dirty = core.tick(DT) or dirty
            next_tick += DT
            if wait < -DT:  # more than a tick late: skip ahead, do not catch up
                log("tick_overrun", behind_ms=round(-wait * 1000, 1))
                next_tick = time.monotonic() + DT
            for event in core.pop_events():
                log(event, tick=core.ticks, state=core.snapshot())

            # Coalesced telemetry: a refused snapshot is not lost. The state stays
            # marked as changed, and a later tick offers a newer snapshot.
            if dirty:
                snapshot = telemetry(core.snapshot(), last_cid, seq + 1)
                if offer_telemetry(q2, limiter, ("simulation/telemetry", encode(snapshot), 0)):
                    seq += 1
                    dirty, last_cid = False, None
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        conn.disconnect().result()
        log("engine_stopped", ticks=core.ticks, snapshots=seq)


if __name__ == "__main__":
    main()