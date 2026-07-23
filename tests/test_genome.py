# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from pathlib import Path

import pytest

from pytierra.adapters.filesystem.genome import load_opcode_map, load_tie
from pytierra.core.errors import AssetError

TIERRA = Path(__file__).resolve().parents[1] / "legacy" / "tierra"
GB0 = TIERRA / "gb0"


def test_load_opcode_map_ok():
    omp = load_opcode_map(GB0 / "opcode.map")
    assert omp.inst_num > 10
    assert "nop0" in omp.by_name
    assert "divide" in omp.by_name


def test_load_opcode_map_missing(tmp_path: Path):
    with pytest.raises(AssetError):
        load_opcode_map(tmp_path / "no.map")


def test_load_opcode_map_empty(tmp_path: Path):
    p = tmp_path / "empty.map"
    p.write_text("# nothing\n", encoding="utf-8")
    with pytest.raises(AssetError):
        load_opcode_map(p)


def test_load_tie_ok(opcode_map):
    gen = load_tie(GB0 / "0080aaa.tie", opcode_map)
    assert gen.meta.genotype == "0080aaa"
    assert len(gen.code) == 80


def test_load_tie_missing(opcode_map, tmp_path: Path):
    with pytest.raises(AssetError):
        load_tie(tmp_path / "x.tie", opcode_map)


def test_load_tie_unknown_mnemonic(opcode_map, tmp_path: Path):
    p = tmp_path / "bad.tie"
    p.write_text(
        "genotype: bad\nCODE\ntrack 0\nnot_a_real_op\n",
        encoding="utf-8",
    )
    with pytest.raises(AssetError, match="Unknown mnemonic"):
        load_tie(p, opcode_map)
