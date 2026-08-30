"""Match two copies of the same finite protocol.

The two copies use different state and action names.
Change one destination to make the exact match fail.
"""
from tempfile import TemporaryDirectory
from pnr12 import PNR

source_states = ["idle", "hello", "auth", "open", "closed"]
source_actions = ["start", "accept", "close"]
source = {
    "idle":   {"start": "hello", "accept": "idle", "close": "closed"},
    "hello":  {"start": "hello", "accept": "auth", "close": "closed"},
    "auth":   {"start": "auth",  "accept": "open", "close": "closed"},
    "open":   {"start": "open",  "accept": "open", "close": "closed"},
    "closed": {"start": "closed", "accept": "closed", "close": "closed"},
}
source_outputs = {
    "idle": "wait", "hello": "hello", "auth": "check", "open": "ready", "closed": "done"
}

target_states = [11, 23, 47, 89, 144]
target_actions = ["x", "y", "z"]
target = {
    11:  {"x": 23,  "y": 11,  "z": 144},
    23:  {"x": 23,  "y": 47,  "z": 144},
    47:  {"x": 47,  "y": 89,  "z": 144},
    89:  {"x": 89,  "y": 89,  "z": 144},
    144: {"x": 144, "y": 144, "z": 144},
}
target_outputs = {11: "wait", 23: "hello", 47: "check", 89: "ready", 144: "done"}

with TemporaryDirectory() as workspace:
    p = PNR(workspace)
    match = p.match_systems(
        source_states,
        source_actions,
        source,
        target,
        target_states,
        target_actions,
        source_observations=source_outputs,
        target_observations=target_outputs,
    )
    state_map = p.externalize(match["tau"], reason="show state map")
    action_map = p.externalize(match["omega"], reason="show action map")
    print("state map:", state_map)
    print("action map:", action_map)
    assert state_map["open"] == 89
    assert action_map["close"] == "z"
    assert p.audit()["status"] == "PASS"
