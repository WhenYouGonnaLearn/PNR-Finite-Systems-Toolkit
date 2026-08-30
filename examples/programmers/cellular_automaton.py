"""Run a circular Rule 30 cellular automaton.

Change WIDTH, STEPS, START, or rule30().
The state count is 2**WIDTH.
"""
from itertools import product
from tempfile import TemporaryDirectory
from pnr12 import PNR

WIDTH = 5
STEPS = 10**100
START = (0, 0, 1, 0, 0)


def rule30(row):
    out = []
    for i in range(WIDTH):
        left = row[(i - 1) % WIDTH]
        center = row[i]
        right = row[(i + 1) % WIDTH]
        out.append(left ^ (center | right))
    return tuple(out)


states = list(product((0, 1), repeat=WIDTH))
transition = {state: rule30(state) for state in states}

with TemporaryDirectory() as workspace:
    p = PNR(workspace)
    program = p.compile_transition(transition, STEPS)
    value = p.run_transition(program["artifact_id"], START, STEPS)
    result = p.externalize(value, reason="show final row")
    print("states:", len(states))
    print("steps:", STEPS)
    print("final row:", result)
    assert len(states) == 32
    assert len(result) == WIDTH
    assert p.audit()["status"] == "PASS"
