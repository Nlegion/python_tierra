# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from scripts.c_compare.acceptance import GOLDEN_FIRST_BIRTH_INST_EXE
from scripts.c_compare.export_python_stats import run_export


def test_export_first_birth_matches_golden():
    out = run_export(until_births=1, sample_every=1000, extra_steps=0)
    assert out["first_birth_InstExe"] == GOLDEN_FIRST_BIRTH_INST_EXE
    assert out["final"]["births"] >= 1
    assert out["size_histogram"].get("80", 0) >= 2
