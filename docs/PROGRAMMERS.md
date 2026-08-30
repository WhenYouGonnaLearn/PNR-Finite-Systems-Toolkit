# PNR12 for programmers

PNR12 works on explicit finite data.

Start with the smallest model that can answer your question. A good model keeps every difference that can change the answer. It removes details that cannot change the answer.

For example, a door controller can have this state:

```text
(lock, power, side, alarm)
```

The full game or application can contain much more data. Do not include that data if it cannot change the door result.

## Basic workflow

1. List the possible states, inputs, actions, or candidates.
2. Write the update rule or check as normal Python code.
3. Build the finite table or candidate list.
4. Run one PNR12 tool on that data.
5. Save the workspace if later work depends on the result.
6. Use `audit()` when you reopen the workspace.

## Main methods

### `PNR(path)`

This method opens a workspace.

```python
from pnr12 import PNR

p = PNR(".pnr")
```

Open the same directory later to load the saved state.

### `audit()`

This method reads the saved records and checks their links.

```python
assert p.audit()["status"] == "PASS"
```

### `add_operation()`

This method stores a complete finite function.

The input rows must cover every permitted input combination. PNR12 checks the rows and stores the function. It does not infer missing rows.

```python
rows = [
    {"in": [-2], "out": -1},
    {"in": [-1], "out": -1},
    {"in": [0],  "out": 0},
    {"in": [1],  "out": 1},
    {"in": [2],  "out": 1},
]

op = p.add_operation(
    "PNR12_BASE",
    "clamp",
    [[-2, -1, 0, 1, 2]],
    [-1, 0, 1],
    evidence=rows[:-1],
    check=rows[-1:],
)
```

### `compile_transition()` and `run_transition()`

Use these methods for repeated deterministic state updates.

If one update is `f(x)`, the compiled program stores jumps for 1, 2, 4, 8, 16, and more updates. PNR12 combines these jumps to reach a large step count.

```python
program = p.compile_transition(transition, max_steps=10**15)
value = p.run_transition(program["artifact_id"], start, 10**15)
result = p.externalize(value, reason="use final state")
```

The set of states must be finite. The `transition` dictionary must contain every state that the update can reach.

### `reduce_machine()`

This method merges finite machine states that have the same output and the same future behavior.

Use it when an implementation has several internal states with the same output and the same future behavior for your current question.

The result reports the number of reduced states in `state_count`. The `state_assignment` dictionary assigns each original state to one reduced state. The `program_id` value identifies the saved program that can run the reduced machine for a long horizon.

### `match_systems()`

This method searches for an exact one-to-one rename between two finite state/action systems.

The rename must preserve every supplied transition. Optional output labels can reduce the search.

Use it to compare small controllers, protocols, or extracted workflows when names are different.

### `find_rewrite()`

This method searches a small expression set for an expression that matches all supplied cases.

The built-in expression set contains variables, addition, subtraction, and finite operations that you add with `add_operation()`.

This is a small search tool. It is not a computer algebra system.

### `search()`

This method checks a finite sequence of candidates.

Your `build` function converts one candidate into an object. Your `qualify` function checks that object. PNR12 returns the first candidate that passes.

Candidate order is part of the policy. Sort the candidates before the call if you want a specific preference order.

```python
result = p.search(
    kind="Configuration",
    candidates=candidates,
    build=build,
    qualify=check,
)
```

The checker is your Python code. PNR12 cannot make an incomplete checker complete.

### `externalize()`

Some methods return a tracked value. The tracked value keeps a link to the saved program that produced it.

Use `externalize()` when you want the plain Python value.

```python
plain_value = p.externalize(value, reason="return to caller")
```

## Simulation experiments

Each simulation below uses a complete finite transition table. The model is small enough to inspect. The step count can be very large because the repeated transition is compiled.

### Cellular automaton

[examples/programmers/cellular_automaton.py](../examples/programmers/cellular_automaton.py) uses a circular Rule 30 row with 5 cells. The model has 32 states. The default run uses `10**100` updates.

Change `WIDTH` to change the state count. The state count is `2**WIDTH`.

Change the rule function to test a different cellular rule.

### Traffic controller

[examples/programmers/traffic_network.py](../examples/programmers/traffic_network.py) models two queues and one signal direction. The model has 32 states. The default run uses `10**80` ticks.

Change `MAX_QUEUE` to change the queue capacity.

Change the arrival conditions to create a different load pattern.

Change the signal switch rule to test a different controller.

### Contact process

[examples/programmers/contact_process.py](../examples/programmers/contact_process.py) uses three sites in a ring. Each site is clear, active, or inactive. The model has 27 states. The default run uses `10**70` ticks.

This is a discrete contact model. It is not an epidemiology model.

Change `SITES` to change the state count. The state count is `3**SITES`.

Change the neighbor rule to test a different network process.

### Factory line

[examples/programmers/factory_line.py](../examples/programmers/factory_line.py) models two machines, two buffers, and a two-tick input clock. The model has 48 states. The default run uses `10**60` ticks.

Change the buffer limits to change storage capacity.

Change the machine phase counts to change process time.

Change the input clock to change the feed rate.

### Discrete ecology

[examples/programmers/discrete_ecology.py](../examples/programmers/discrete_ecology.py) uses prey, predators, food, and season as bounded integer state values. The model has 48 states. The default run uses `10**50` ticks.

This is a programming model. It is not a biological forecast.

Change the value ranges to change the state count.

Change the update rule to test a different feedback system.

## Structural experiments

The repository also includes smaller examples for machine reduction, system matching, expression search, finite operation storage, and parameter search.

See [examples/programmers/README.md](../examples/programmers/README.md).

## Model size

Finite models can become large very quickly.

A model with five fields of size 10 has `10**5` states. A model with ten Boolean fields has `2**10` states.

Keep a field only if it can change the result that you need.

When the state table becomes too large to construct or inspect, use a different tool or find a smaller state description.

## Workspaces

See [WORKSPACES.md](WORKSPACES.md) for restart behavior, file locking, `audit()`, and external anchors.

## Limits

PNR12 does not interpret source code, images, logs, or natural language. Convert the part you need into explicit finite data first.

PNR12 does not replace numerical solvers, SAT or SMT solvers, computer algebra systems, databases, or machine-learning libraries.

PNR12 is most useful when the finite part of a larger problem is important enough to save, check, repeat, or reuse.
