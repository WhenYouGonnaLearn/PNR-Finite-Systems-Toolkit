# Model and agent examples

These examples show small finite tasks that can run beside a language model or agent.

The surrounding system selects the task data. PNR12 checks or repeats the explicit finite part.

- `bounded_candidate_search.py` checks an ordered list of configuration candidates.
- `long_horizon_inner_loop.py` runs a finite workflow controller for `10**18` steps.
- `state_reduction.py` merges duplicate states in a generated workflow.
- `structural_match.py` matches two finite processes by transition structure.
- `dependency_invalidation.py` rejects dependent work after a saved assumption fails.
- `durable_job.py` uses two Python processes with the same workspace.

Run the complete example set with:

```text
python verify_examples.py
```

## How to modify the examples

Reorder candidates before `search()`.

Increase the step horizon in the workflow example.

Change one transition before state reduction or structure matching.

Change the assumption that the durable job invalidates.

Use a stable workspace path when you adapt the durable example to a real long-running job.
