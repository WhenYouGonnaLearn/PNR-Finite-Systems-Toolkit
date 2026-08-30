# PNR12 guide for language models and agents

This document is separate from the programmer guide.

Use PNR12 for a subtask when you can convert that subtask into explicit finite data and a Python check. Finite data has a known set of possible values.

A language model can still read source material, interpret requirements, choose a model, propose candidates, and decide what new evidence means. PNR12 can store and repeat the parts that are already explicit.

## Good uses beside a model

PNR12 can help a model with these jobs:

- check a finite list of candidates with the same Python rules;
- run a deterministic state update for a very large number of steps;
- merge duplicate states in a finite workflow;
- match two finite processes that use different names;
- save compact task state across process restarts;
- keep dependencies between saved results;
- invalidate dependent work after an input or assumption fails.

PNR12 does not read arbitrary text or source code for the model. The surrounding system must convert the relevant part into finite data first.

## Operating pattern

### 1. State the question

Write one sentence that identifies the result that must remain correct.

Example:

```text
Which controller state can occur after a valid sequence of retry events?
```

### 2. Select the finite fields

Keep only fields that can change the result.

Example:

```text
(phase, retry_count, test_status, blocked)
```

### 3. Build explicit data

Create a transition table, candidate list, state machine, or set of test cases.

Do this outside PNR12. The model or normal Python code can perform this step.

### 4. Use a deterministic check

For candidate work, put the acceptance rule in Python.

```python
result = p.search(
    kind="Configuration",
    candidates=ordered_candidates,
    build=build_candidate,
    qualify=check_candidate,
)
```

`search()` returns the first passing candidate. Order the list before the call when one passing candidate is better than another.

See [examples/models/bounded_candidate_search.py](examples/models/bounded_candidate_search.py).

### 5. Move repeated finite work out of the model loop

A long task can contain a small controller that repeats for many steps. Compile that controller once.

```python
program = p.compile_transition(transition, max_steps=10**18)
value = p.run_transition(program["artifact_id"], start, 10**18)
```

The model can inspect the start state, update rule, and final state without performing every intermediate update in tokens.

See [examples/models/long_horizon_inner_loop.py](examples/models/long_horizon_inner_loop.py).

### 6. Reduce duplicate workflow states

A generated workflow can contain several labels that behave the same way. Use `reduce_machine()` when the outputs and future transitions are explicit.

See [examples/models/state_reduction.py](examples/models/state_reduction.py).

### 7. Compare structure instead of names

Use `match_systems()` when two extracted finite processes can have different labels but should have the same transitions.

See [examples/models/structural_match.py](examples/models/structural_match.py).

### 8. Save important dependencies

Record a source fact before you save a conclusion that depends on it.

If later evidence rejects that source fact, invalidate the dependent saved work.

See [examples/models/dependency_invalidation.py](examples/models/dependency_invalidation.py).

### 9. Continue across process restarts

Use a stable workspace path for a long job.

Open the same path in the next process. Run `audit()` before you continue.

The [durable job example](examples/models/durable_job.py) uses two Python processes. The second process opens the first process workspace. It checks saved state, rejects one earlier assumption, and continues the job.

## Example set

| Example | Input from the model or surrounding code | PNR12 task |
| --- | --- | --- |
| [bounded_candidate_search.py](examples/models/bounded_candidate_search.py) | ordered configuration candidates | return the first candidate that passes the Python check |
| [long_horizon_inner_loop.py](examples/models/long_horizon_inner_loop.py) | finite workflow state and update rule | run `10**18` workflow updates |
| [state_reduction.py](examples/models/state_reduction.py) | workflow states, outputs, and transitions | merge duplicate states |
| [structural_match.py](examples/models/structural_match.py) | two finite process models | find an exact rename between them |
| [dependency_invalidation.py](examples/models/dependency_invalidation.py) | source facts and dependent checks | reject dependent work after a source fact fails |
| [durable_job.py](examples/models/durable_job.py) | a persistent finite job model | save, exit, reopen, check, invalidate, and continue |

## Long-horizon work

A long-running agent usually has two different kinds of state.

External state includes source files, messages, tool results, user goals, and new observations. Keep this state in the agent system.

Finite task state can include phases, counters, test status, retry state, selected candidates, and dependency links. PNR12 can store and operate on this state when the possible values are explicit.

Do not convert a large task into a huge finite table only to use PNR12. Use it for the compact part that you can state and check with explicit rules.

## Failure handling

A saved result can still be wrong when the finite model or Python checker is wrong.

When new evidence shows that an input assumption is false, record that change and invalidate dependent work. Then return to the surrounding model for interpretation and a new plan.

## How to modify the examples

Change one item at a time.

Increase a horizon to test repeated execution.

Add one state field to test model growth.

Remove one output label before state reduction.

Change one transition before structure matching.

Reorder the candidate list before bounded search.

Change one saved assumption before the durable job resumes.

These changes show which part of the task PNR12 checks and which part remains the responsibility of the surrounding system.
