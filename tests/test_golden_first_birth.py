# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Regression: instructions to first 0080aaa birth must stay stable (mut=0)."""

from tests.conftest import GOLDEN_FIRST_BIRTH_INST_EXE


def test_inst_exe_to_first_birth_golden(make_vm):
    vm = make_vm(max_instructions=300_000)
    assert int(vm.config.get("GeneBnker", 0) or 0) == 0
    vm.start()
    vm.run(until_births=1)
    assert vm.inst_exe == GOLDEN_FIRST_BIRTH_INST_EXE
    assert vm.counters["births"] >= 1
