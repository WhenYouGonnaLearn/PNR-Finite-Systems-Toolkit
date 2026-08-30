"""Reject dependent work after a saved assumption fails.

Change the assumption ID or the required field to test the dependency rules.
"""
from tempfile import TemporaryDirectory
from pnr12 import PNR, PNRError

with TemporaryDirectory() as workspace:
    p = PNR(workspace)
    p.add_assumption("A", "the parser accepts empty sections")
    p.require("claim", ["behavior"], assumptions=["A"])
    evidence = p.observe(True, ["behavior"], ["direct-test"])

    p.assess_claim("claim", [evidence], assumptions=["A"])
    print("dependent check accepted before the failed assumption")

    p.refute("empty-section-failure", falsified_assumptions=["A"])

    q = PNR(workspace)
    try:
        q.assess_claim("claim", [evidence], assumptions=["A"])
    except PNRError:
        print("dependent check rejected after the failed assumption")
    else:
        raise AssertionError("failed assumption was accepted")

    assert q.audit()["status"] == "PASS"
