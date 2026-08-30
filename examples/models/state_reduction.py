"""Reduce duplicate states in a generated workflow.

The workflow has eight visible stages and four duplicate lanes.
Change one output or transition to keep a state separate.
"""
from tempfile import TemporaryDirectory
from pnr12 import PNR

STAGES = ("read", "map", "plan", "edit", "build", "test", "review", "save")
LANES = ("a", "b", "c", "d")
states = [f"{stage}_{lane}" for stage in STAGES for lane in LANES]
observations = {f"{stage}_{lane}": stage for stage in STAGES for lane in LANES}
transitions = {}
for i, stage in enumerate(STAGES):
    next_stage = STAGES[(i + 1) % len(STAGES)]
    for lane in LANES:
        transitions[f"{stage}_{lane}"] = {"next": f"{next_stage}_{lane}"}

with TemporaryDirectory() as workspace:
    p = PNR(workspace)
    reduced = p.reduce_machine(
        states,
        observations,
        transitions,
        action="next",
        max_steps=10**9,
    )
    print("original states:", len(states))
    print("reduced states:", reduced["state_count"])
    assert len(states) == 32
    assert reduced["state_count"] == 8
    assert p.audit()["status"] == "PASS"
