# Derivative work of Tierra Simulator — see legacy/tierra/license.h
import pytest

from pytierra.core.errors import InternalError
from pytierra.services.rng import TierraRNG


def test_rng_deterministic_sequence():
    a = TierraRNG()
    b = TierraRNG()
    a.tsrand(42)
    b.tsrand(42)
    seq_a = [a.tlrand() for _ in range(20)]
    seq_b = [b.tlrand() for _ in range(20)]
    assert seq_a == seq_b
    assert all(isinstance(x, int) for x in seq_a)


def test_rng_tirand_tcrand_range():
    r = TierraRNG()
    r.tsrand(1)
    for _ in range(50):
        assert 0 <= r.tirand() <= 32767
        assert 0 <= r.tcrand() <= 127
        assert 0.0 <= r.tdrand() < 1.0


def test_rng_snapshot_restore():
    r = TierraRNG()
    r.tsrand(99)
    _ = [r.tlrand() for _ in range(5)]
    snap = r.snapshot()
    nxt = r.tlrand()
    r.restore(snap)
    assert r.tlrand() == nxt


def test_tdrand_index_guard():
    from pytierra.services.rng import M3, _trand_index

    # After % M3, RandIx3 is in [0, M3); M3 itself yields j=98 (invariant fail).
    with pytest.raises(InternalError, match="index out of range"):
        _trand_index(M3)
    assert 1 <= _trand_index(0) <= 97
    assert 1 <= _trand_index(M3 - 1) <= 97
