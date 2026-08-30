# Programmer experiments

Run an experiment from the repository root.

```text
python examples/programmers/traffic_network.py
```

Each file defines a finite model and checks its own result.

## Simulations

- `cellular_automaton.py` uses 32 states and runs `10**100` updates.
- `traffic_network.py` uses 32 traffic-controller states and runs `10**80` ticks.
- `contact_process.py` uses 27 contact-network states and runs `10**70` ticks.
- `factory_line.py` uses 48 production-line states and runs `10**60` ticks.
- `discrete_ecology.py` uses 48 bounded population states and runs `10**50` ticks.

These files are programming models. They are not scientific forecasts.

## Other tools

- `controller_reduction.py` merges duplicate controller states.
- `protocol_match.py` finds an exact rename between two finite protocols.
- `rewrite_expression.py` finds a short expression that matches supplied cases.
- `finite_operation.py` stores and checks a complete finite function.
- `parameter_search.py` checks an ordered list of finite parameter settings.

## How to experiment

Change one constant or one rule.

Run the file again.

Check the printed state count.

Increase a range only when the complete state table still fits in memory.

Add an assertion when you expect a specific result.
