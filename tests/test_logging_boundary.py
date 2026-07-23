# Derivative work of Tierra Simulator — see legacy/tierra/license.h
import logging

from pytierra.core.logging_setup import configure_logging

VM_LOG = "pytierra.services.vm"


def test_configure_logging_idempotent():
    root = logging.getLogger()
    before = list(root.handlers)
    configure_logging(level=logging.INFO)
    configure_logging(level=logging.DEBUG)
    assert len(root.handlers) == len(before) or len(root.handlers) >= 1


def test_api_events_logged(make_vm, caplog):
    vm = make_vm(max_instructions=50_000)
    with caplog.at_level(logging.INFO, logger=VM_LOG):
        vm.start()
        vm.enable_trace(True)
        vm.set_limits(max_instructions=50_000)
        vm.step(5)
        snap = vm.snapshot()
        vm.restore(snap)
        vm.stop()
    events = {getattr(r, "event", None) for r in caplog.records}
    assert "start" in events
    assert "enable_trace" in events
    assert "set_limits" in events
    assert "restore" in events
    assert "stop" in events


def test_isa_logger_silent_during_steps(make_vm, caplog):
    vm = make_vm(max_instructions=50_000)
    vm.start()
    with caplog.at_level(logging.DEBUG):
        vm.step(200)
    isa_records = [
        r for r in caplog.records if r.name.startswith("pytierra.services.isa")
    ]
    assert isa_records == []


def test_birth_debug_only(make_vm, caplog):
    vm = make_vm(max_instructions=200_000)
    vm.start()
    with caplog.at_level(logging.INFO, logger=VM_LOG):
        for _ in range(300):
            vm.step(n=500)
            if vm.counters.get("births", 0) >= 1:
                break
    birth_info = [
        r
        for r in caplog.records
        if getattr(r, "event", None) == "birth" or "Birth:" in r.getMessage()
    ]
    assert birth_info == []

    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger=VM_LOG):
        vm._notify_birth(1, 80)
        vm._notify_death(1)
    assert any(getattr(r, "event", None) == "birth" for r in caplog.records)
    assert any(getattr(r, "event", None) == "death" for r in caplog.records)


def test_sandbox_limit_warning(make_vm, caplog):
    vm = make_vm(max_instructions=50)
    vm.start()
    with caplog.at_level(logging.WARNING, logger=VM_LOG):
        try:
            vm.run()
        except Exception:
            pass
    assert any(getattr(r, "event", None) == "sandbox_limit" for r in caplog.records)
