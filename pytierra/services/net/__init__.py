# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""NET ports: in-memory transport only (no sockets in VM)."""

from pytierra.services.net.memory_transport import InMemoryTransport
from pytierra.services.net.migration import accept_immigrant, offer_emigrant

__all__ = ["InMemoryTransport", "accept_immigrant", "offer_emigrant"]
