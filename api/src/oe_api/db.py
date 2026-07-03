"""Per-request session/store wiring. Tests override `get_store`."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request

from oe_store.store import GraphStore


def get_store(request: Request) -> Iterator[GraphStore]:
    factory = request.app.state.session_factory
    with factory() as session:
        yield GraphStore(session)
