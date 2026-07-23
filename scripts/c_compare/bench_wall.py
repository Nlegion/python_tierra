# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Wall-clock benchmark: Python always; optional C binary."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.c_compare.acceptance import acceptance_config_dict  # noqa: E402

from pytierra import TierraVM  # noqa: E402
from pytierra.adapters.filesystem.genome import load_opcode_map  # noqa: E402
from pytierra.adapters.filesystem.soup_in import parse_soup_in  # noqa: E402
from pytierra.bootstrap.wiring import load_genomes_into_vm  # noqa: E402
from pytierra.core.errors import SandboxLimitError  # noqa: E402
from pytierra.models.limits import SandboxLimits  # noqa: E402


def _bench_python(*, until_births: int, soup_in: Path | None, asset_root: Path) -> dict:
    limits = SandboxLimits(
        max_instructions=max(500_000, until_births * 20_000),
        wall_time_s=600,
    )
    if soup_in is not None:
        cfg = parse_soup_in(soup_in.read_text(encoding="utf-8"))
        opmap = load_opcode_map(asset_root / "gb0" / "opcode.map")
        vm = TierraVM(
            config=cfg,
            asset_root=asset_root,
            opcode_map=opmap,
            limits=limits,
        )
        load_genomes_into_vm(vm, asset_root / "gb0")
    else:
        vm = TierraVM.from_config(
            acceptance_config_dict(),
            asset_root=asset_root,
            limits=limits,
        )
    t0 = time.perf_counter()
    vm.start()
    try:
        st = vm.run(until_births=until_births)
    except SandboxLimitError as exc:
        st = {**vm.stats(), "error": str(exc)}
    wall = time.perf_counter() - t0
    return {
        "wall_time_s": wall,
        "InstExe": st.get("InstExe"),
        "births": st.get("births"),
        "deaths": st.get("deaths"),
        "NumCells": st.get("NumCells"),
    }


def _bench_c(
    *,
    c_bin: Path,
    c_workdir: Path,
    soup_in: Path | None,
    extra: list[str],
    timeout: float,
) -> dict:
    cmd = [str(c_bin), *extra]
    if soup_in is not None:
        (c_workdir / "soup_in").write_text(
            soup_in.read_text(encoding="utf-8"), encoding="utf-8"
        )
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=str(c_workdir),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    wall = time.perf_counter() - t0
    return {
        "wall_time_s": wall,
        "returncode": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
        "cmd": cmd,
        "cwd": str(c_workdir),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--until-births", type=int, default=80)
    p.add_argument("--out", type=Path, default=ROOT / "viz" / "bench_wall.json")
    p.add_argument("--asset-root", type=Path, default=ROOT / "legacy" / "tierra")
    p.add_argument("--soup-in", type=Path, default=None, help="Optional soup_in text file")
    p.add_argument("--c-bin", type=Path, default=None, help="Path to Tierra C binary")
    p.add_argument("--c-workdir", type=Path, default=None, help="C process cwd (soup_in here)")
    p.add_argument("--c-extra-arg", action="append", default=[], help="Extra argv for C binary")
    p.add_argument("--c-timeout", type=float, default=600.0)
    args = p.parse_args()

    result: dict = {
        "python": _bench_python(
            until_births=args.until_births,
            soup_in=args.soup_in,
            asset_root=args.asset_root,
        ),
        "c": None,
    }
    if args.c_bin is None:
        result["c_skipped"] = "no --c-bin"
    else:
        work = args.c_workdir or args.c_bin.parent
        result["c"] = _bench_c(
            c_bin=args.c_bin,
            c_workdir=work,
            soup_in=args.soup_in,
            extra=list(args.c_extra_arg),
            timeout=args.c_timeout,
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
