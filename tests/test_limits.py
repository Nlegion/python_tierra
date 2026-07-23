# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Sandbox host budget tests (see also test_errors_api / test_0080aaa_replicate)."""

import time

import pytest

from pytierra.core.errors import SandboxLimitError


def test_max_instructions_raises_and_set_limits_continues(make_vm):
    vm = make_vm(max_instructions=150)
    vm.start()
    with pytest.raises(SandboxLimitError) as ei:
        vm.run()
    assert ei.value.kind == "max_instructions"
    vm.set_limits(max_instructions=10_000)
    assert vm.step(20) > 0


def test_wall_time_limit(make_vm):
    vm = make_vm(max_instructions=10_000_000, wall_time_s=0.01)
    vm.start()
    # force run_started in the past so wall check trips quickly
    vm._run_started = time.perf_counter() - 1.0
    with pytest.raises(SandboxLimitError) as ei:
        vm._check_limits(force=True)
    assert ei.value.kind == "wall_time_s"


def test_max_cells_soft_fail_documented(make_vm):
    """max_cells blocks birth via alloc_cell=None; does not raise SandboxLimitError."""
    vm = make_vm(max_cells=1, max_instructions=5_000)
    vm.start()
    assert vm.alloc_cell() is None
    vm.step(50)
    assert vm.queues.num_cells == 1
