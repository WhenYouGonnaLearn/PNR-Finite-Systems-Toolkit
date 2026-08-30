# PNR-FST workspaces

A workspace is a directory that stores PNR-FST records.

Use a stable path when work must continue after the current Python process ends.

## Create or open a workspace

```python
from pnr12 import PNR

p = PNR(".pnr")
```

The first call creates the workspace. A later call reads the saved records.

## Check a workspace

Run `audit()` after you open important saved work.

```python
p = PNR(".pnr")
assert p.audit()["status"] == "PASS"
```

The check reads the saved record chain and active dependency links.

## Continue after a restart

A program can stop and later open the same directory.

Process 1:

```python
from pnr12 import PNR

p = PNR("job.pnr")
# Save work here.
assert p.audit()["status"] == "PASS"
```

Process 2:

```python
from pnr12 import PNR

p = PNR("job.pnr")
assert p.audit()["status"] == "PASS"
# Continue work here.
```

The model example [examples/models/durable_job.py](../examples/models/durable_job.py) runs a complete two-process demonstration.

## Detect an older restored copy

A workspace can be internally valid and still be old. This can happen when a backup restores the complete directory.

Use `anchor()` when your application must detect this case.

```python
p = PNR("job.pnr")
anchor = p.anchor()
```

Store the anchor outside `job.pnr`.

Later, open the workspace with the saved anchor:

```python
p = PNR("job.pnr", expect_anchor=anchor)
```

The external location is required. If a backup restores the workspace and the anchor together, the anchor cannot show that a newer workspace once existed.

## Concurrent writers

PNR-FST uses an operating-system file lock while it appends records. The Linux path uses `fcntl`. The Windows path uses `msvcrt`.

Do not copy or replace workspace files while a process is writing to them.

## Backups

Close active writers before you copy a workspace directory.

Keep the external anchor separate if you use rollback detection.
