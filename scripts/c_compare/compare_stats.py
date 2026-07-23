# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Compare Python vs C exported stats JSON (±5% on key metrics)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _pct_ok(a: float, b: float, tol: float = 0.05) -> bool:
    if a == 0 and b == 0:
        return True
    base = max(abs(a), abs(b), 1.0)
    return abs(a - b) / base <= tol


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("python_json", type=Path)
    ap.add_argument("c_json", type=Path)
    ap.add_argument("--tol", type=float, default=0.05)
    args = ap.parse_args()
    py = json.loads(args.python_json.read_text(encoding="utf-8"))
    c = json.loads(args.c_json.read_text(encoding="utf-8"))
    ok = True
    pairs = [
        ("first_birth_InstExe", py.get("first_birth_InstExe"), c.get("first_birth_InstExe")),
        ("final.births", py["final"].get("births"), c["final"].get("births")),
        ("final.deaths", py["final"].get("deaths"), c["final"].get("deaths")),
        ("final.NumCells", py["final"].get("NumCells"), c["final"].get("NumCells")),
    ]
    for name, a, b in pairs:
        if a is None or b is None:
            print(f"SKIP {name}: missing")
            continue
        good = _pct_ok(float(a), float(b), args.tol)
        print(f"{'OK' if good else 'FAIL'} {name}: python={a} c={b}")
        ok = ok and good
    # size histogram: max bucket share abs diff
    ph = {int(k): v for k, v in py.get("size_histogram", {}).items()}
    ch = {int(k): v for k, v in c.get("size_histogram", {}).items()}
    pt = sum(ph.values()) or 1
    ct = sum(ch.values()) or 1
    keys = set(ph) | set(ch)
    max_diff = 0.0
    for k in keys:
        max_diff = max(max_diff, abs(ph.get(k, 0) / pt - ch.get(k, 0) / ct))
    hist_ok = max_diff <= args.tol
    print(f"{'OK' if hist_ok else 'FAIL'} size_histogram max_share_diff={max_diff:.4f}")
    ok = ok and hist_ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
