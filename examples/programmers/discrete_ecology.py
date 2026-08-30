"""Run a bounded population and resource model.

State is (prey, predators, food, season). This is a programming model.
Change the ranges, STEPS, START, or tick().
"""
from itertools import product
from tempfile import TemporaryDirectory
from pnr12 import PNR

PREY = range(4)
PREDATORS = range(3)
FOOD = range(2)
SEASONS = range(2)
STEPS = 10**50
START = (3, 1, 1, 0)


def clamp(value, low, high):
    return max(low, min(high, value))


def tick(state):
    prey, predators, food, season = state

    food2 = 1 if season == 0 and prey <= 2 else 0

    prey2 = prey
    if food and predators == 0:
        prey2 += 1
    if predators >= 2 and prey > 0:
        prey2 -= 1
    if prey == 0 and food2:
        prey2 = 1
    prey2 = clamp(prey2, 0, 3)

    predators2 = predators
    if prey >= 3:
        predators2 += 1
    if prey <= 1 and predators > 0:
        predators2 -= 1
    predators2 = clamp(predators2, 0, 2)

    return prey2, predators2, food2, (season + 1) % 2


states = list(product(PREY, PREDATORS, FOOD, SEASONS))
transition = {state: tick(state) for state in states}
assert all(next_state in transition for next_state in transition.values())

with TemporaryDirectory() as workspace:
    p = PNR(workspace)
    program = p.compile_transition(transition, STEPS)
    value = p.run_transition(program["artifact_id"], START, STEPS)
    result = p.externalize(value, reason="show final population state")
    print("states:", len(states))
    print("steps:", STEPS)
    print("final state:", result)
    assert len(states) == 48
    assert result in transition
    assert p.audit()["status"] == "PASS"
