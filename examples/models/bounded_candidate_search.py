"""Check an ordered list of configuration candidates.

search() returns the first candidate that passes.
Change the sort key, limits, or candidate ranges.
"""
from itertools import product
from tempfile import TemporaryDirectory
from pnr12 import PNR

raw_candidates = list(product(
    (8, 16, 24, 32, 48, 64, 96, 128),
    range(1, 7),
    range(1, 11),
))


def build(candidate):
    batch, workers, chunks = candidate
    return {
        "batch": batch,
        "workers": workers,
        "chunks": chunks,
        "memory_mb": batch * workers * 2 + chunks * 8,
        "throughput": batch * workers,
        "latency_score": chunks * workers,
    }


def check(config):
    if config["memory_mb"] > 700:
        raise ValueError("memory limit")
    if config["throughput"] < 256:
        raise ValueError("throughput limit")
    if config["latency_score"] > 30:
        raise ValueError("latency limit")
    return {"accepted": True}


# The sort order is the preference rule for this example.
candidates = sorted(raw_candidates, key=lambda c: (build(c)["memory_mb"], -build(c)["throughput"], c))

with TemporaryDirectory() as workspace:
    p = PNR(workspace)
    result = p.search(
        kind="Configuration",
        candidates=candidates,
        build=build,
        qualify=check,
    )
    print("candidate count:", len(candidates))
    print("first passing candidate:", result["candidate"])
    print("check result:", result["verification"])
    assert len(candidates) == 480
    assert check(build(result["candidate"])) == {"accepted": True}
    assert p.audit()["status"] == "PASS"
