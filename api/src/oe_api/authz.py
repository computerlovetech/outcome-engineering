"""Per-graph authorization: identity → membership/share token → role."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Path

from oe_api.auth import Principal, get_principal
from oe_api.db import get_store
from oe_store.models import Graph
from oe_store.store import GraphStore

ROLE_ORDER = {"viewer": 0, "editor": 1, "owner": 2}


@dataclass
class GraphAccess:
    graph: Graph
    role: str
    via_share: bool = False


def _resolve_access(graph_ref: str, principal: Principal, store: GraphStore) -> GraphAccess:
    graph = store.get_graph(graph_ref)
    if graph is None:
        raise HTTPException(status_code=404, detail=f"no graph matches {graph_ref!r}")

    if principal.user is not None:
        membership = store.membership(graph.id, principal.user.id)
        if membership is None:
            raise HTTPException(status_code=403, detail="you are not a member of this graph")
        return GraphAccess(graph=graph, role=membership.role)

    if principal.share_graph_id == graph.id:
        return GraphAccess(graph=graph, role="viewer", via_share=True)

    raise HTTPException(status_code=401, detail="authentication required")


def require_graph_role(min_role: str):
    def dependency(
        graph_ref: str = Path(),
        principal: Principal = Depends(get_principal),
        store: GraphStore = Depends(get_store),
    ) -> GraphAccess:
        access = _resolve_access(graph_ref, principal, store)
        if ROLE_ORDER[access.role] < ROLE_ORDER[min_role]:
            raise HTTPException(
                status_code=403,
                detail=f"this operation requires the {min_role} role; you are a {access.role}",
            )
        return access

    return dependency


graph_viewer = require_graph_role("viewer")
graph_editor = require_graph_role("editor")
graph_owner = require_graph_role("owner")
