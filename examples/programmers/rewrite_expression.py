"""Find a short expression that matches all supplied cases.

Change the expected values or add a finite operation with add_operation().
"""
from tempfile import TemporaryDirectory
from pnr12 import PNR

source_expr = {
    "op": "sub",
    "args": [
        {"op": "add", "args": [{"var": "x"}, {"var": "y"}]},
        {"var": "y"},
    ],
}

cases = [
    {"env": {"x": -30, "y": 17}, "expected": -30},
    {"env": {"x": -3, "y": 7}, "expected": -3},
    {"env": {"x": 0, "y": 4}, "expected": 0},
    {"env": {"x": 2, "y": -9}, "expected": 2},
    {"env": {"x": 11, "y": 5}, "expected": 11},
    {"env": {"x": 200, "y": -40}, "expected": 200},
]

with TemporaryDirectory() as workspace:
    p = PNR(workspace)
    rewrite = p.find_rewrite(source_expr, cases[:-2], cases[-2:])
    replacement = p.externalize(rewrite["replacement"], reason="show replacement")
    print("replacement:", replacement)
    assert replacement == {"var": "x"}
    assert p.audit()["status"] == "PASS"
