import pytest

from engine.simulation_core import SimulationCore

DT = 1.0 / 60

def run(core, seconds):
    for _ in range(round(seconds / DT)):
        core.tick(DT)

def test_wheel_speeds_drive_and_turn_the_robot():
    straight = SimulationCore()
    straight.apply({"control": "throttle", "value": 1.0})
    run(straight, 0.5)
    assert straight.state["left"] == straight.state["right"] == 1.0
    assert straight.state["x"] == pytest.approx(0.5)  # 1 m/s for 0.5 s
    assert straight.state["y"] == pytest.approx(0.0)

    spinner = SimulationCore()
    spinner.apply({"control": "steer", "value": 1.0})
    run(spinner, 0.5)
    assert spinner.state["left"] == -1.0 and spinner.state["right"] == 1.0
    assert spinner.state["heading"] == pytest.approx(1.0)  # 2 rad/s for 0.5 s
    assert spinner.state["x"] == 0.0 and spinner.state["y"] == 0.0  # on the spot

def test_resend_keeps_the_robot_going_but_changes_nothing():
    core = SimulationCore()
    assert core.apply({"control": "throttle", "value": 1.0}) == {"throttle": 1.0}
    run(core, 0.9)
    assert core.apply({"control": "throttle", "value": 1.0}) == {}  # a re-send
    run(core, 0.9)
    assert core.state["throttle"] == 1.0  # 1.8 s in, no deadman stop

def test_deadman_stops_the_robot():
    core = SimulationCore()
    core.apply({"control": "throttle", "value": 1.0})
    run(core, 1.1)  # no command for over a second
    assert core.state["throttle"] == 0.0
    assert "deadman_stop" in core.pop_events()
    assert core.state["left"] == core.state["right"] == 0.0

def test_robot_comes_to_rest_and_goes_quiet():
    core = SimulationCore()
    assert core.tick(DT) is False  # a new robot is at rest
    core.apply({"control": "throttle", "value": 1.0})
    run(core, 0.5)
    core.apply({"control": "throttle", "value": 0.0})
    assert core.tick(DT) is True  # the stop itself is reported once
    assert core.state["left"] == core.state["right"] == 0.0
    assert core.tick(DT) is False  # at rest: no telemetry needed

@pytest.mark.parametrize("value", [True, "1", float("nan"), 1.5])
def test_bad_values_are_refused(value):
    with pytest.raises(ValueError):
        SimulationCore().apply({"control": "throttle", "value": value})