"""Run a finite workflow controller for a long horizon.

The surrounding system defines the phases and update rule.
Change PHASES, RETRIES, STEPS, or next_state().
"""
from itertools import product
from tempfile import TemporaryDirectory
from pnr12 import PNR

PHASES = ("inspect", "plan", "edit", "test", "review", "checkpoint")
RETRIES = range(8)
STEPS = 10**18
START = ("inspect", 0)


def next_state(state):
    phase, retry = state
    if phase == "inspect":
        return "plan", retry
    if phase == "plan":
        return "edit", retry
    if phase == "edit":
        return "test", retry
    if phase == "test":
        return ("review", retry) if retry == 7 else ("inspect", retry + 1)
    if phase == "review":
        return "checkpoint", retry
    return "inspect", 0


states = list(product(PHASES, RETRIES))
transition = {state: next_state(state) for state in states}
assert all(next_state_value in transition for next_state_value in transition.values())

with TemporaryDirectory() as workspace:
    p = PNR(workspace)
    program = p.compile_transition(transition, STEPS)
    value = p.run_transition(program["artifact_id"], START, STEPS)
    result = p.externalize(value, reason="show workflow state")
    print("states:", len(states))
    print("steps:", STEPS)
    print("final state:", result)
    assert result in transition
    assert p.audit()["status"] == "PASS"
