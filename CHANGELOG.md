# Changelog

## 1.3.0

Version 1.3.0 replaces repeated 1.2.x code paths with a smaller shared implementation.

- `pnr12.py` has 581 physical lines and 56,179 bytes.
- The previous 60-test file passes without changes.
- Ten regression tests cover defects found after 1.2.1.
- A new finite operation is saved in one complete record.
- A new helper is saved in one complete record.
- Saved `set` and `frozenset` values keep different types.
- Key pairs such as `False` and `0` are rejected when Python would merge them.
- Work-limit accounting handles common floating-point boundary cases.
- A missing dependency is rejected before PNR12 saves the dependent result.
- Invalid helper input is reported as `PNRError`.
- Concurrent-write and saved-file checks were tightened.
- Windows file locking uses `msvcrt`.
- Common tasks have shorter public method names.
- Programmer and model documentation are separate.
- The repository has 15 executable examples across several finite problem types.
- `verify.py` runs the complete advertised release check by default.
- `verify.py --quick` runs the deterministic subset.
