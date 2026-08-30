# PNR-FST 1.3.0 release checks

This file lists the checks for this release.

The checks apply only to the package features and inputs that they exercise.

## Source size

`pnr12.py` has **574 physical Python lines** and **56,083 bytes**.

The public 1.3.0 build before this repair pass had **581 lines**, **56,179 bytes**, and **64,257 bytes** after `ast.unparse()`. The release checker does not permit the core to exceed any of those three values.

The older size reference is **966 lines** and **64,272 bytes**.

Python 3.13 expands the current module with `ast.unparse()` to **64,250 bytes**. This check reduces the benefit of dense source formatting.

Source size does not show that two programs have identical behavior.

## Deterministic tests

The main regression file has **60 tests**. One test was corrected in this pass. It now limits finite-operation work by the number of table rows instead of a candidate count that the implementation never searched.

The attack file has **19 tests**. Ten cover defects found before the first public 1.3.0 build. Nine additional checks cover this repair pass.

The combined result is **79 of 79 tests passed**.

The new checks cover these cases:

- store one transition table instead of a table ladder for large update counts;
- reject an oversized system-match search before permutation work starts;
- charge finite-operation work by rows that are actually checked;
- preserve transform input, type, loss flag, and detail;
- reject Python key collisions during machine reduction;
- use example rows to select a rewrite and separate check rows to test it;
- contain invalid rewrite candidate operations instead of leaking Python exceptions;
- remove unused metadata parameters from the helper proposal API;
- use both the selected claim and the supplied value when choosing an experiment.

The earlier regression checks still cover saved type identity, key collisions, read-only views, work-limit arithmetic, missing dependencies, typed helper failures, complete record writes, changed saved payloads, and exported plain values.

## Random tests

`stress.py` runs two generated test sets.

The first set saves nested typed values, closes the workspace, opens it again, and runs `audit()`. The release test uses **300 cases**.

The second set generates finite transition tables. It compares large-step execution with a separate cycle-based Python implementation. The release test uses **200 cases** with update counts up to one million.

Generated tests can find defects. They do not prove behavior for every possible input.

## Example checks

`verify_examples.py` runs every file in `examples/programmers/` and `examples/models/` in a new Python process.

The current package has **16 examples**.

The programmer set includes five finite simulations and five smaller tool examples.

The model set includes six workflow examples. One example opens the same workspace from two separate Python processes.

## Documentation checks

`verify.py` checks local Markdown links.

It also scans public Markdown files and example files for retired internal terms and selected generated-text patterns.

This scan is a regression check. It does not replace human editing.

## File and platform checks

`verify.py` compiles every shipped Python file.

The Linux file-lock path was run in the release environment.

The Windows `msvcrt` path is in the CI matrix. The Linux release environment did not run that Windows path.

## Run the checks

Run all release checks:

```text
python verify.py
```

Run only source, documentation, compile, and deterministic test checks:

```text
python verify.py --quick
```

You can also run the longer groups separately:

```text
python stress.py
python verify_examples.py --group programmers
python verify_examples.py --group models
```

The runtime uses only the Python standard library.

## Test limits

The release checks do not cover arbitrary Python callbacks or every file system. They also do not cover every process failure point or unsupported input form.
