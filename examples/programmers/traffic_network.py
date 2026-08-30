"""Run a two-queue traffic controller for a long horizon.

Change MAX_QUEUE, STEPS, the arrival rule, or the signal rule.
"""
from itertools import product
from tempfile import TemporaryDirectory
from pnr12 import PNR

MAX_QUEUE = 3
STEPS = 10**80
START = (0, 0, 0)


def tick(state):
    north, east, green = state

    if green == 0:
        east = min(MAX_QUEUE, east + 1)
        if north:
            north -= 1
    else:
        north = min(MAX_QUEUE, north + 1)
        if east:
            east -= 1

    if (green == 0 and north == 0) or (green == 1 and east == 0):
        green = 1 - green
    if north == MAX_QUEUE and green == 1:
        green = 0
    if east == MAX_QUEUE and green == 0:
        green = 1

    return north, east, green


states = list(product(range(MAX_QUEUE + 1), range(MAX_QUEUE + 1), range(2)))
transition = {state: tick(state) for state in states}
assert all(next_state in transition for next_state in transition.values())

with TemporaryDirectory() as workspace:
    p = PNR(workspace)
    program = p.compile_transition(transition, STEPS)
    value = p.run_transition(program["artifact_id"], START, STEPS)
    result = p.externalize(value, reason="show final traffic state")
    print("states:", len(states))
    print("steps:", STEPS)
    print("final state:", result)
    assert len(states) == 32
    assert result in transition
    assert p.audit()["status"] == "PASS"
