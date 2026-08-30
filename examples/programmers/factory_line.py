"""Run a small two-machine production line.

State tracks two buffers, two machine flags, and an input clock.
Change the limits, machine rules, or input rule.
"""
from itertools import product
from tempfile import TemporaryDirectory
from pnr12 import PNR

RAW_MAX = 2
MID_MAX = 1
STEPS = 10**60
START = (0, 0, 0, 0, 0)


def tick(state):
    raw, middle, machine_a, machine_b, clock = state

    if clock == 0:
        raw = min(RAW_MAX, raw + 1)

    if machine_a and middle < MID_MAX:
        middle += 1
        machine_a = 0
    elif not machine_a and raw > 0:
        raw -= 1
        machine_a = 1

    if machine_b:
        machine_b = 0
    elif middle > 0:
        middle -= 1
        machine_b = 1

    return raw, middle, machine_a, machine_b, (clock + 1) % 2


states = list(product(
    range(RAW_MAX + 1),
    range(MID_MAX + 1),
    range(2),
    range(2),
    range(2),
))
transition = {state: tick(state) for state in states}
assert all(next_state in transition for next_state in transition.values())

with TemporaryDirectory() as workspace:
    p = PNR(workspace)
    program = p.compile_transition(transition, STEPS)
    value = p.run_transition(program["artifact_id"], START, STEPS)
    result = p.externalize(value, reason="show final factory state")
    print("states:", len(states))
    print("steps:", STEPS)
    print("final state:", result)
    assert len(states) == 48
    assert result in transition
    assert p.audit()["status"] == "PASS"
