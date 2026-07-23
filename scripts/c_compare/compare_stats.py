# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Compare Python vs C exported stats JSON.

Tolerances:
- ≤5% → OK
- >5% and ≤10% → WARN (exit 0)
- >10% → FAIL (exit 1)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _rel_diff(a: float, b: float) -> float:
    base = max(abs(a), abs(b), 1.0)
    return abs(a - b) / base


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("python_json", type=Path)
    ap.add_argument("c_json", type=Path)
    ap.add_argument("--tol", type=float, default=0.05, help="pass band")
    ap.add_argument("--fail-tol", type=float, default=0.10, help="hard fail band")
    args = ap.parse_args()
    py = json.loads(args.python_json.read_text(encoding="utf-8"))
    c = json.loads(args.c_json.read_text(encoding="utf-8"))
    failed = False
    warned = False

    def check(name: str, a, b) -> None:
        nonlocal failed, warned
        if a is None or b is None:
            print(f"SKIP {name}: missing")
            return
        d = _rel_diff(float(a), float(b))
        if d > args.fail_tol:
            print(f"FAIL {name}: python={a} c={b} rel_diff={d:.4f}")
            failed = True
        elif d > args.tol:
            print(f"WARN {name}: python={a} c={b} rel_diff={d:.4f}")
            warned = True
        else:
            print(f"OK {name}: python={a} c={b}")

    check("first_birth_InstExe", py.get("first_birth_InstExe"), c.get("first_birth_InstExe"))
    check("final.births", py["final"].get("births"), c["final"].get("births"))
    check("final.deaths", py["final"].get("deaths"), c["final"].get("deaths"))
    check("final.NumCells", py["final"].get("NumCells"), c["final"].get("NumCells"))
    if "unique_genotypes" in py or "unique_genotypes" in c:
        check(
            "unique_genotypes",
            py.get("unique_genotypes", py["final"].get("unique_genotypes")),
            c.get("unique_genotypes", c["final"].get("unique_genotypes")),
        )

    ph = {int(k): v for k, v in py.get("size_histogram", {}).items()}
    ch = {int(k): v for k, v in c.get("size_histogram", {}).items()}
    pt = sum(ph.values()) or 1
    ct = sum(ch.values()) or 1
    keys = set(ph) | set(ch)
    max_diff = 0.0
    for k in keys:
        max_diff = max(max_diff, abs(ph.get(k, 0) / pt - ch.get(k, 0) / ct))
    if max_diff > args.fail_tol:
        print(f"FAIL size_histogram max_share_diff={max_diff:.4f}")
        failed = True
    elif max_diff > args.tol:
        print(f"WARN size_histogram max_share_diff={max_diff:.4f}")
        warned = True
    else:
        print(f"OK size_histogram max_share_diff={max_diff:.4f}")

    if failed:
        return 1
    if warned:
        print("completed with warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
