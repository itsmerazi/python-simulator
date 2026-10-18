import math

INPUTS = {"throttle": (-1.0, 1.0), "steer": (-1.0, 1.0)}  # control -> allowed range
INPUT_TIMEOUT = 1.0   # deadman: simulated seconds without any command
MAX_SPEED = 1.0       # m/s of one wheel at full command
WHEEL_BASE = 1.0      # distance between the two wheels, in metres
ARENA = 10.0          # the robot stays within +/- 10 m on both axes

def _clamp(value, low, high):
    return max(low, min(high, value))

def _number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))

class SimulationCore:
    # Owns the whole state. No I/O, no clock, no MQTT, no JSON: plain Python only.

    def __init__(self):
        self.state = {"throttle": 0.0, "steer": 0.0, "x": 0.0, "y": 0.0,
                      "heading": 0.0, "left": 0.0, "right": 0.0}
        self.ticks = 0
        self._since_input = 0.0
        self._events = []

    def apply(self, payload):
        # Commands are absolute setpoints, so applying one twice is harmless.
        # Returns what changed: {} when the command repeats the current value.
        control, value = payload.get("control"), payload.get("value")
        if control not in INPUTS:
            raise ValueError("unknown_control")
        if not _number(value):
            raise ValueError("bad_value")
        low, high = INPUTS[control]
        if not low <= value <= high:
            raise ValueError("out_of_range")
        self._since_input = 0.0  # any valid command keeps the robot going
        if self.state[control] == value:
            return {}  # a re-send: nothing changed
        self.state[control] = float(value)
        return {control: self.state[control]}

    def tick(self, dt):
        # One fixed step of dt seconds. Returns True when the state changed.
        s = self.state
        self.ticks += 1
        self._since_input += dt
        changed = False
        if self._since_input > INPUT_TIMEOUT and (s["throttle"] or s["steer"]):
            s["throttle"] = s["steer"] = 0.0  # deadman: the inputs went quiet
            self._events.append("deadman_stop")
            changed = True
        # Differential drive: mix the two inputs into one speed for each wheel.
        before = (s["left"], s["right"])
        s["left"] = _clamp(s["throttle"] - s["steer"], -1.0, 1.0) * MAX_SPEED
        s["right"] = _clamp(s["throttle"] + s["steer"], -1.0, 1.0) * MAX_SPEED
        if s["left"] == 0.0 and s["right"] == 0.0:
            return changed or before != (0.0, 0.0)  # at rest: nothing moves
        forward = (s["left"] + s["right"]) / 2        # m/s along the heading
        turn = (s["right"] - s["left"]) / WHEEL_BASE  # rad/s, positive = left
        s["heading"] = (s["heading"] + turn * dt) % (2 * math.pi)
        s["x"] = _clamp(s["x"] + forward * math.cos(s["heading"]) * dt, -ARENA, ARENA)
        s["y"] = _clamp(s["y"] + forward * math.sin(s["heading"]) * dt, -ARENA, ARENA)
        return True

    def snapshot(self):
        # Rounded to keep telemetry and log lines small
        return {key: round(value, 3) for key, value in self.state.items()}

    def pop_events(self):
        # Events such as "deadman_stop", for main.py to log.
        events, self._events = self._events, []
        return events