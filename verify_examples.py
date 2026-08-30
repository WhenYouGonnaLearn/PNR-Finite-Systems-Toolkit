"""Run shipped examples in new Python processes."""
from __future__ import annotations
import argparse
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--group",
        choices=("all", "programmers", "models"),
        default="all",
        help="select the example group",
    )
    args = parser.parse_args()

    files = []
    if args.group in ("all", "programmers"):
        files += sorted((ROOT / "examples" / "programmers").glob("*.py"))
    if args.group in ("all", "models"):
        files += sorted((ROOT / "examples" / "models").glob("*.py"))

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    for path in files:
        print(f"== {path.relative_to(ROOT)} ==", flush=True)
        subprocess.run(
            [sys.executable, str(path)],
            cwd=ROOT,
            env=env,
            check=True,
            timeout=60,
        )
    print(f"examples PASS: {len(files)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
