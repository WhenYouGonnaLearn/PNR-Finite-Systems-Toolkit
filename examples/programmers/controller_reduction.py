"""Reduce a controller that has duplicate internal states.

The controller has six visible stages and four duplicate lanes.
Change one output or transition to prevent a merge.
"""
from tempfile import TemporaryDirectory
from pnr12 import PNR

STAGES = ("idle", "load", "run", "check", "cool", "done")
LANES = ("A", "B", "C", "D")
states = [f"{stage}_{lane}" for stage in STAGES for lane in LANES]
observations = {f"{stage}_{lane}": stage for stage in STAGES for lane in LANES}

transitions = {}
for stage_index, stage in enumerate(STAGES):
    next_stage = STAGES[(stage_index + 1) % len(STAGES)]
    for lane in LANES:
        transitions[f"{stage}_{lane}"] = {"next": f"{next_stage}_{lane}"}

with TemporaryDirectory() as workspace:
    p = PNR(workspace)
    reduced = p.reduce_machine(
        states,
        observations,
        transitions,
        action="next",
        max_steps=10**12,
    )
    print("original states:", len(states))
    print("reduced states:", reduced["state_count"])
    assert len(states) == 24
    assert reduced["state_count"] == 6

    start = reduced["state_assignment"]["idle_A"]
    value = p.run_transition(reduced["program_id"], start, 10**12)
    result = p.externalize(value, reason="show reduced controller state")
    print("state after long run:", result)
    assert p.audit()["status"] == "PASS"
