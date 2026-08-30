"""Run the release checks for PNR12 1.3.0."""
from __future__ import annotations
import argparse
import ast
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
PROTO4_LINES = 966
PROTO4_BYTES = 64272
BANNED_TERMS = (
    "occurrence fabric", "court", "courts", "constitution", "constitutions",
    "standing", "aperture", "apertures", "fibre", "fibres", "genesis",
    "reasoner", "reasoning runtime", "semantic", "synthesis", "provenance",
    "qualified", "qualification", "representation lattice", "protected surface",
    "sidecar", "geometry", "geometric", "lattice", "quotient",
    "quotienting", "fiber", "fibers", "surface", "coordinate",
    "projection", "topology", "topological", "manifold", "embedding",
    "carrier", "representation geometry", "input space", "state space",
    "equivalent states", "region", "trajectory", "refinement", "coarsening",
    "representation", "dimension", "metric",
)
BANNED_STYLE = (
    "this is useful", "deliberately", "simply", "just ", "obviously",
    "clearly", "powerful", "robust", "seamless", "leverage", "utilize",
)
LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def run(*args: str) -> None:
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def public_files() -> list[pathlib.Path]:
    docs = list(ROOT.rglob("*.md"))
    examples = list((ROOT / "examples").rglob("*.py"))
    return sorted(docs + examples)


def check_public_text() -> None:
    for path in public_files():
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        hits = [term for term in BANNED_TERMS if term in lower]
        if hits:
            raise SystemExit(f"public text gate failed in {path.relative_to(ROOT)}: {hits}")
        style_hits = [term for term in BANNED_STYLE if term in lower]
        if style_hits:
            raise SystemExit(f"public style gate failed in {path.relative_to(ROOT)}: {style_hits}")
        if re.search(r"(?:^|[.!?]\s+|\n)no\s+[^\n.!?]{1,80}[.!?]", lower):
            raise SystemExit(f"public style gate failed in {path.relative_to(ROOT)}: standalone 'No ...' sentence")


def check_links() -> None:
    for path in ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for target in LINK.findall(text):
            target = target.split("#", 1)[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                raise SystemExit(f"broken link in {path.relative_to(ROOT)}: {target}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--quick",
        action="store_true",
        help="run source, documentation, compile, and deterministic test checks only",
    )
    args = parser.parse_args()

    source = (ROOT / "pnr12.py").read_bytes()
    text = source.decode()
    lines = len(text.splitlines())
    if not (lines < PROTO4_LINES and len(source) < PROTO4_BYTES):
        raise SystemExit(f"size gate failed: {lines} lines / {len(source)} bytes")

    normalized = (ast.unparse(ast.parse(text)) + "\n").encode()
    if len(normalized) >= PROTO4_BYTES:
        raise SystemExit(f"expanded source size failed: {len(normalized)} bytes")

    check_public_text()
    check_links()

    py_files = [
        str(path.relative_to(ROOT))
        for path in ROOT.rglob("*.py")
        if "__pycache__" not in path.parts
    ]
    run("-m", "py_compile", *py_files)
    run("-m", "unittest", "test_pnr12", "test_attack")

    if not args.quick:
        run("stress.py")
        run("verify_examples.py")

    mode = "quick" if args.quick else "full"
    print(
        f"{mode} checks PASS: {lines} lines / {len(source)} bytes; "
        f"expanded {len(normalized)} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
