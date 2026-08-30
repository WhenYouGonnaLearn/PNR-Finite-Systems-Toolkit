# PNR-FST

PNR-FST is a small Python toolkit for explicit finite systems.

A finite model has a known set of states, inputs, actions, or candidates. PNR-FST stores these items in a workspace and provides tools that operate on them.

The package has one Python module, `pnr12`, and one workspace directory.

```text
finite model
    |
    v
check, reduce, match, or compile
    |
    v
saved result
    |
    +--> reuse later
    +--> check after restart
    +--> invalidate dependent work if an input changes
```

PNR-FST is a good fit when you can write the important part of a problem as explicit finite data. It can help with repeated state updates, finite machine reduction, exact structure matching, small expression searches, candidate checks, and persistent task state.

Use another tool for continuous numerical simulation, large matrix computation, unrestricted SAT or SMT, statistical learning, symbolic algebra, or open-ended text interpretation.

## Install

```text
python -m pip install .
```

PNR-FST requires Python 3.11 or later. The runtime uses only the Python standard library.

## Quick example

This example uses a traffic controller with two queues. The full state has 32 possible values. The code builds the complete transition table once. PNR-FST returns the controller state after `10**80` updates.

```python
from itertools import product
from tempfile import TemporaryDirectory
from pnr12 import PNR

MAX_QUEUE = 3
STEPS = 10**80

states = list(product(
    range(MAX_QUEUE + 1),  # north queue
    range(MAX_QUEUE + 1),  # east queue
    range(2),              # green direction
))


def tick(state):
    north, east, green = state

    if green == 0:
        east = min(MAX_QUEUE, east + 1)
        if north:
            north -= 1
    else:
        north = min(MAX_QUEUE, north + 1)
        if east:
            east -= 1

    if (green == 0 and north == 0) or (green == 1 and east == 0):
        green = 1 - green
    if north == MAX_QUEUE and green == 1:
        green = 0
    if east == MAX_QUEUE and green == 0:
        green = 1

    return north, east, green


transition = {state: tick(state) for state in states}

with TemporaryDirectory() as workspace:
    p = PNR(workspace)
    program = p.compile_transition(transition, STEPS)
    value = p.run_transition(program["artifact_id"], (0, 0, 0), STEPS)
    print(p.externalize(value, reason="show final traffic state"))
```

Change the queue limit, arrival pattern, signal rule, start state, or step count. The state count grows with the product of the state ranges.

## Experiments

The repository includes executable examples. Each example has a small model and one or more values that you can change.

### Simulations

| Experiment | Model size | Requested update count | Main control |
| --- | ---: | ---: | --- |
| [Cellular automaton](examples/programmers/cellular_automaton.py) | 32 states | `10**100` | row width and rule |
| [Traffic controller](examples/programmers/traffic_network.py) | 32 states | `10**80` | queue limit and signal rule |
| [Contact process](examples/programmers/contact_process.py) | 27 states | `10**70` | network size and update rule |
| [Factory line](examples/programmers/factory_line.py) | 48 states | `10**60` | buffer limits and machine timing |
| [Discrete ecology](examples/programmers/discrete_ecology.py) | 48 states | `10**50` | population limits and update rules |

These are programming models. They are not scientific forecasts.

### Other tools

| Task | Main method | Example |
| --- | --- | --- |
| Reduce duplicate machine states | `reduce_machine()` | [controller_reduction.py](examples/programmers/controller_reduction.py) |
| Match two finite systems | `match_systems()` | [protocol_match.py](examples/programmers/protocol_match.py) |
| Find a small matching expression | `find_rewrite()` | [rewrite_expression.py](examples/programmers/rewrite_expression.py) |
| Store a complete finite operation | `add_operation()` | [finite_operation.py](examples/programmers/finite_operation.py) |
| Check an ordered candidate list | `search()` | [parameter_search.py](examples/programmers/parameter_search.py) |

## Documentation

Programmers should start with [docs/PROGRAMMERS.md](docs/PROGRAMMERS.md).

Workspace and restart behavior is in [docs/WORKSPACES.md](docs/WORKSPACES.md).

Language-model and agent use is in the separate [MODEL_GUIDE.md](MODEL_GUIDE.md).

Release checks and tested limits are in [VERIFY.md](VERIFY.md).

## Workspace

`PNR(path)` opens or creates a workspace directory. PNR-FST reads the saved records when you open the workspace again. `audit()` checks the saved record chain and active dependency links.

```python
from pnr12 import PNR

p = PNR(".pnr")
print(p.audit()["status"])
```

See [docs/WORKSPACES.md](docs/WORKSPACES.md) before you use a workspace across process restarts or backups.

## License

MIT. See [LICENSE](LICENSE).
