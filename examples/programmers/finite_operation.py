"""Store a complete finite operation.

Change the input values, output values, or one row.
"""
from tempfile import TemporaryDirectory
from pnr12 import PNR

rows = [
    {"in": [-3], "out": -1},
    {"in": [-2], "out": -1},
    {"in": [-1], "out": -1},
    {"in": [0], "out": 0},
    {"in": [1], "out": 1},
    {"in": [2], "out": 1},
    {"in": [3], "out": 1},
]

with TemporaryDirectory() as workspace:
    p = PNR(workspace)
    op = p.add_operation(
        "PNR12_BASE",
        "clamp",
        [[-3, -2, -1, 0, 1, 2, 3]],
        [-1, 0, 1],
        evidence=rows[:-2],
        check=rows[-2:],
    )
    print("saved operation set:", op["language_id"])
    assert op["language_id"] in p.languages
    assert p.audit()["status"] == "PASS"
