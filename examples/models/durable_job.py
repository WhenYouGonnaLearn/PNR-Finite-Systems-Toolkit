"""Run one finite job across two Python processes.

Run this file with no arguments for a complete demonstration.
Use `stage1 PATH` and `stage2 PATH` to inspect each process separately.
"""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from pnr12 import PNR, PNRError

PHASES = ("inspect", "edit", "test", "save")
RETRIES = range(4)
STEPS = 10**12
START = ("inspect", 0)


def next_state(state):
    phase, retry = state
    if phase == "inspect":
        return "edit", retry
    if phase == "edit":
        return "test", retry
    if phase == "test":
        return ("save", retry) if retry == 3 else ("inspect", retry + 1)
    return "inspect", 0


def stage1(root):
    root = Path(root)
    workspace = root / "job.pnr"
    checkpoint = root / "checkpoint.json"

    p = PNR(workspace)
    candidates = [(chunk, retries) for chunk in (8, 16, 32, 64) for retries in range(1, 5)]

    def build(candidate):
        chunk, retries = candidate
        return {"chunk": chunk, "retries": retries, "work": chunk * retries}

    def check(candidate):
        if candidate["work"] < 64:
            raise ValueError("work floor")
        if candidate["work"] > 128:
            raise ValueError("work ceiling")
        return {"accepted": True}

    choice = p.search(
        kind="JobSetting",
        candidates=candidates,
        build=build,
        qualify=check,
    )

    p.add_assumption("input-v1", "input format version 1 is accepted")
    p.require("ready-v1", ["input-check"], assumptions=["input-v1"])
    evidence = p.observe(True, ["input-check"], ["direct-test"])
    p.assess_claim("ready-v1", [evidence], assumptions=["input-v1"])

    states = [(phase, retry) for phase in PHASES for retry in RETRIES]
    transition = {state: next_state(state) for state in states}
    program = p.compile_transition(transition, STEPS)
    checkpoint.write_text(json.dumps({
        "evidence": evidence,
        "program": program["artifact_id"],
        "candidate": choice["candidate"],
    }))

    print("selected candidate:", choice["candidate"])
    print("stage 1 audit:", p.audit()["status"])
    print("stage 1 records:", len(p.occurrences))


def stage2(root):
    root = Path(root)
    workspace = root / "job.pnr"
    checkpoint = json.loads((root / "checkpoint.json").read_text())

    p = PNR(workspace)
    print("stage 2 reopen audit:", p.audit()["status"])
    print("saved candidate:", checkpoint["candidate"])

    value = p.run_transition(checkpoint["program"], START, STEPS)
    print("resumed workflow state:", p.externalize(value, reason="show resumed workflow state"))

    p.refute("input-v1-failed", falsified_assumptions=["input-v1"])
    try:
        p.assess_claim("ready-v1", [checkpoint["evidence"]], assumptions=["input-v1"])
    except PNRError:
        print("old dependent check rejected")
    else:
        raise AssertionError("old dependent check was accepted")

    p.add_assumption("input-v2", "input format version 2 is accepted")
    p.require("ready-v2", ["input-check-v2"], assumptions=["input-v2"])
    evidence2 = p.observe(True, ["input-check-v2"], ["direct-test-v2"])
    p.assess_claim("ready-v2", [evidence2], assumptions=["input-v2"])
    print("continued job audit:", p.audit()["status"])
    print("continued records:", len(p.occurrences))


def demo():
    with TemporaryDirectory() as temp:
        here = Path(__file__).resolve()
        subprocess.run([sys.executable, str(here), "stage1", temp], check=True)
        subprocess.run([sys.executable, str(here), "stage2", temp], check=True)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        demo()
    elif len(sys.argv) == 3 and sys.argv[1] == "stage1":
        stage1(sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == "stage2":
        stage2(sys.argv[2])
    else:
        raise SystemExit("usage: durable_job.py [stage1|stage2 PATH]")
