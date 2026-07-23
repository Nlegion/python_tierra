# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from pathlib import Path

import pytest

from pytierra.adapters.filesystem.soup_in import parse_soup_in
from pytierra.core.errors import SandboxLimitError
from pytierra.models.limits import SandboxLimits
from pytierra.services.vm.service import TierraVM

TIERRA = Path(__file__).resolve().parents[1] / "legacy" / "tierra"


def test_soup_size_limit_at_create(opcode_map):
    cfg = parse_soup_in("SoupSize = 9999999\nNumCells = 0\nseed = 1\n")
    with pytest.raises(SandboxLimitError) as ei:
        TierraVM(
            config=cfg,
            asset_root=TIERRA,
            opcode_map=opcode_map,
            limits=SandboxLimits(max_soup_size=1000),
        )
    assert ei.value.kind == "max_soup_size"
