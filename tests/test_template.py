# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from pathlib import Path

from pytierra.adapters.filesystem.genome import load_opcode_map, load_tie
from pytierra.services.isa.template import ctemplate
from pytierra.services.memory.soup import SoupMemory

GB0 = Path(__file__).resolve().parents[1] / "legacy" / "tierra" / "gb0"


def test_0080aaa_templates_found():
    omp = load_opcode_map(GB0 / "opcode.map")
    gen = load_tie(GB0 / "0080aaa.tie", omp)
    mem = SoupMemory(soup_size=256)
    for i, op in enumerate(gen.code):
        mem.soup[i] = op
    # adrb at IP=9 looks backward for complement of following nop0*4
    # beginning marker is nop1*4 at 0..3; complement of nop0 is nop1
    ip = 9  # adrb
    # source template at 10..13 = nop0*4
    adrt, mode, _ = ctemplate(
        mem,
        ip=ip,
        f_start=14 + 1,
        b_start=10 - 4 - 1,
        slim=400,
        tz=4,
        direction="b",
        nop0=omp.nop0,
        nop1=omp.nop1,
        nop_s=omp.nop_s,
        min_templ_size=1,
        mode_pref=2,
    )
    assert adrt >= 0
    # address after beginning template (nop1*4) => 4
    assert adrt == 4
