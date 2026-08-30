"""Check an ordered list of finite parameter settings.

search() returns the first setting that passes.
Change the ranges, sort key, or limits.
"""
from itertools import product
from tempfile import TemporaryDirectory
from pnr12 import PNR

raw = list(product((8, 16, 24, 32, 48, 64), range(1, 6), range(1, 5)))


def build(setting):
    block, workers, depth = setting
    return {
        "block": block,
        "workers": workers,
        "depth": depth,
        "memory": block * workers + 12 * depth,
        "work": block * workers * depth,
    }


def check(item):
    if item["memory"] > 220:
        raise ValueError("memory limit")
    if item["work"] < 256:
        raise ValueError("work floor")
    return {"accepted": True}


settings = sorted(raw, key=lambda value: (build(value)["memory"], -build(value)["work"], value))

with TemporaryDirectory() as workspace:
    p = PNR(workspace)
    result = p.search(
        kind="ParameterSet",
        candidates=settings,
        build=build,
        qualify=check,
    )
    print("settings:", len(settings))
    print("first passing setting:", result["candidate"])
    assert len(settings) == 120
    assert check(build(result["candidate"])) == {"accepted": True}
    assert p.audit()["status"] == "PASS"
