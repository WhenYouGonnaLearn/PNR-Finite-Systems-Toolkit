"""Run a discrete contact process on a ring.

Each site is clear, active, or inactive. This is a programming model.
Change SITES, STEPS, START, or tick().
"""
from itertools import product
from tempfile import TemporaryDirectory
from pnr12 import PNR

SITES = 3
STEPS = 10**70
START = (0, 1, 0)

CLEAR = 0
ACTIVE = 1
INACTIVE = 2


def tick(sites):
    out = []
    for i, value in enumerate(sites):
        left = sites[(i - 1) % SITES]
        right = sites[(i + 1) % SITES]
        if value == ACTIVE:
            out.append(INACTIVE)
        elif value == CLEAR and (left == ACTIVE or right == ACTIVE):
            out.append(ACTIVE)
        elif value == INACTIVE and left == INACTIVE and right == INACTIVE:
            out.append(CLEAR)
        else:
            out.append(value)
    return tuple(out)


states = list(product((CLEAR, ACTIVE, INACTIVE), repeat=SITES))
transition = {state: tick(state) for state in states}
assert all(next_state in transition for next_state in transition.values())

with TemporaryDirectory() as workspace:
    p = PNR(workspace)
    program = p.compile_transition(transition, STEPS)
    value = p.run_transition(program["artifact_id"], START, STEPS)
    result = p.externalize(value, reason="show final contact state")
    print("states:", len(states))
    print("steps:", STEPS)
    print("final state:", result)
    assert len(states) == 27
    assert result in transition
    assert p.audit()["status"] == "PASS"
