"""Compare two finite workflows by transition structure.

The workflows use different names.
Change one edge to make the exact match fail.
"""
from tempfile import TemporaryDirectory
from pnr12 import PNR

left_states = ["read", "map", "edit", "test", "save"]
left_actions = ["next", "retry", "reset"]
left = {
    "read": {"next": "map", "retry": "read", "reset": "read"},
    "map": {"next": "edit", "retry": "map", "reset": "read"},
    "edit": {"next": "test", "retry": "edit", "reset": "read"},
    "test": {"next": "save", "retry": "edit", "reset": "read"},
    "save": {"next": "read", "retry": "save", "reset": "read"},
}
left_outputs = {"read": 0, "map": 1, "edit": 2, "test": 3, "save": 4}

right_states = [101, 203, 307, 409, 503]
right_actions = ["a", "b", "c"]
right = {
    101: {"a": 203, "b": 101, "c": 101},
    203: {"a": 307, "b": 203, "c": 101},
    307: {"a": 409, "b": 307, "c": 101},
    409: {"a": 503, "b": 307, "c": 101},
    503: {"a": 101, "b": 503, "c": 101},
}
right_outputs = {101: 0, 203: 1, 307: 2, 409: 3, 503: 4}

with TemporaryDirectory() as workspace:
    p = PNR(workspace)
    match = p.match_systems(
        left_states,
        left_actions,
        left,
        right,
        right_states,
        right_actions,
        source_observations=left_outputs,
        target_observations=right_outputs,
    )
    state_map = p.externalize(match["tau"], reason="show workflow state map")
    action_map = p.externalize(match["omega"], reason="show workflow action map")
    print("state map:", state_map)
    print("action map:", action_map)
    assert state_map["test"] == 409
    assert action_map["next"] == "a"
    assert p.audit()["status"] == "PASS"
