# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from pytierra.services.metrics import MetricsRecorder


def test_recorder_birth_and_samples(make_vm):
    vm = make_vm(max_instructions=300_000)
    rec = MetricsRecorder(sample_every=200)
    vm.attach_recorder(rec)
    vm.start()
    vm.run(until_births=1)
    assert any(e["kind"] == "birth" for e in rec.events)
    assert rec.samples
    assert rec.samples[-1]["births"] >= 1
    edges = rec.birth_edges(max_edges=10)
    assert isinstance(edges, list)
