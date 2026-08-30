# PNR12 1.3.0 release checks

This file lists the checks for this release.

The checks apply only to the tested package features and test inputs.

## Source size

`pnr12.py` has **581 physical Python lines** and **56,179 bytes**.

The size reference is **966 lines** and **64,272 bytes**.

Python 3.13 expands the current module with `ast.unparse()` to **64,257 bytes**. This check reduces the benefit of dense source formatting.

Source size does not show that two programs have identical behavior.

## Deterministic tests

The unchanged 1.2.1 test file passes **60 of 60 tests** against 1.3.0.

A second test file adds **10 regression tests** for defects found after 1.2.1.

The combined result is **70 of 70 tests passed**.

The added tests cover these cases:

- save `set` and `frozenset` as different types;
- reject dictionary key pairs such as `False` and `0` when Python merges them;
- block changes through public read-only views;
- handle a `0.3` work limit after charges of `0.1` and `0.2`;
- reject a missing dependency;
- report invalid helper input as `PNRError`;
- save a new finite operation in one complete record;
- save a new helper in one complete record;
- detect a changed saved payload;
- keep an exported plain value independent from its producer.

## Random tests

`stress.py` runs two generated test sets.

The first set saves nested typed values, closes the workspace, opens it again, and runs `audit()`. The release test uses **300 cases**.

The second set generates finite transition tables. It compares long repeated execution with a separate cycle-based Python implementation. The release test uses **200 cases** with horizons up to one million steps.

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
