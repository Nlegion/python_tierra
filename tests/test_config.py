# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from pathlib import Path

import pytest

from pytierra.adapters.filesystem.soup_in import load_soup_in, parse_soup_in
from pytierra.core.errors import AssetError


def test_parse_known_and_unknown(caplog):
    text = """
SoupSize = 4096
SliceSize = 10
NotARealKey = 1
center
0080aaa
"""
    with caplog.at_level("WARNING"):
        cfg = parse_soup_in(text)
    assert cfg.soup_size == 4096
    assert cfg.slice_size == 10
    assert cfg.place_center is True
    assert cfg.inoculum == ["0080aaa"]
    assert "NotARealKey" in cfg.unknown_keys
    assert any("unknown soup_in key" in r.message for r in caplog.records)


def test_parse_float_and_defaults():
    cfg = parse_soup_in("MovPropThrDiv = .7\n")
    assert cfg.values["MovPropThrDiv"] == pytest.approx(0.7)
    assert cfg.seed == 1
    assert cfg.genebank_path == "gb0/"


def test_load_soup_in_missing(tmp_path: Path):
    with pytest.raises(AssetError):
        load_soup_in(tmp_path / "missing.cfg")


def test_load_soup_in_ok(tmp_path: Path):
    p = tmp_path / "soup_in"
    p.write_text("SoupSize = 100\nseed = 7\n", encoding="utf-8")
    cfg = load_soup_in(p)
    assert cfg.soup_size == 100
    assert cfg.seed == 7
