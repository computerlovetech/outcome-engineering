from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from oe_api import serialize
from oe_api.auth import require_user
from oe_api.authz import GraphAccess, graph_owner, graph_viewer
from oe_api.db import get_store
from oe_api.schemas import GraphCreate, GraphPatch, MemberPut
from oe_core.model import valid_slug
from oe_store.models import Graph, User
from oe_store.store import GraphStore

router = APIRouter()


def _graph_payload(graph: Graph, role: str | None = None) -> dict:
    payload = {
        "id": str(graph.id),
        "slug": graph.slug,
        "name": graph.name,
        "createdAt": graph.created_at.isoformat(),
    }
    if role is not None:
        payload["role"] = role
    return payload


@router.get("/graphs")
def list_graphs(user: User = Depends(require_user), store: GraphStore = Depends(get_store)) -> dict:
    return {"graphs": [_graph_payload(graph, role) for graph, role in store.graphs_for_user(user.id)]}


@router.post("/graphs", status_code=201)
def create_graph(
    body: GraphCreate,
    user: User = Depends(require_user),
    store: GraphStore = Depends(get_store),
) -> dict:
    if not valid_slug(body.slug):
        raise HTTPException(status_code=400, detail=f"invalid graph slug {body.slug!r}; use lowercase letters, digits, and single hyphens")
    if store.graph_slug_taken(body.slug):
        raise HTTPException(status_code=409, detail=f"a graph with slug {body.slug!r} already exists")
    graph = store.create_graph(slug=body.slug, name=body.name, owner_id=user.id)
    store.session.commit()
    return _graph_payload(graph, "owner")


@router.get("/graphs/{graph_ref}")
def get_graph(access: GraphAccess = Depends(graph_viewer)) -> dict:
    return _graph_payload(access.graph, access.role)


@router.patch("/graphs/{graph_ref}")
def patch_graph(
    body: GraphPatch,
    access: GraphAccess = Depends(graph_owner),
    store: GraphStore = Depends(get_store),
) -> dict:
    if body.name is not None:
        access.graph.name = body.name
    store.session.commit()
    return _graph_payload(access.graph, access.role)


@router.delete("/graphs/{graph_ref}", status_code=204)
def delete_graph(
    access: GraphAccess = Depends(graph_owner),
    store: GraphStore = Depends(get_store),
) -> None:
    store.delete_graph(access.graph)
    store.session.commit()


# --- overview / tree / validate ------------------------------------------------

@router.get("/graphs/{graph_ref}/overview")
def graph_overview(
    access: GraphAccess = Depends(graph_viewer),
    store: GraphStore = Depends(get_store),
) -> dict:
    snapshot = store.load_snapshot(access.graph.id)
    read_only = access.via_share or access.role == "viewer"
    return {"graph": _graph_payload(access.graph, access.role), **serialize.graph_overview_payload(snapshot, read_only=read_only)}


@router.get("/graphs/{graph_ref}/tree")
def graph_tree(
    access: GraphAccess = Depends(graph_viewer),
    store: GraphStore = Depends(get_store),
) -> dict:
    return serialize.tree_payload(store.load_snapshot(access.graph.id))


@router.get("/graphs/{graph_ref}/validate")
def graph_validate(
    access: GraphAccess = Depends(graph_viewer),
    store: GraphStore = Depends(get_store),
) -> dict:
    return serialize.validation_payload(store.load_snapshot(access.graph.id))


# --- members --------------------------------------------------------------------

@router.get("/graphs/{graph_ref}/members")
def list_members(
    access: GraphAccess = Depends(graph_viewer),
    store: GraphStore = Depends(get_store),
) -> dict:
    return {
        "members": [
            {
                "userId": str(m.user_id),
                "email": m.user.email,
                "name": m.user.name,
                "role": m.role,
            }
            for m in store.members(access.graph.id)
        ]
    }


def _resolve_member_user(store: GraphStore, user_ref: str) -> User:
    try:
        user = store.get_user(uuid.UUID(user_ref))
    except ValueError:
        user = store.find_user_by_email(user_ref)
    if user is None:
        raise HTTPException(
            status_code=404,
            detail=f"no user matches {user_ref!r}; they must log in once before being added",
        )
    return user


@router.put("/graphs/{graph_ref}/members/{user_ref}")
def put_member(
    user_ref: str,
    body: MemberPut,
    access: GraphAccess = Depends(graph_owner),
    store: GraphStore = Depends(get_store),
) -> dict:
    target = _resolve_member_user(store, user_ref)
    membership = store.set_member(access.graph.id, target.id, body.role)
    _ensure_an_owner_remains(store, access, changing_user_id=target.id)
    store.session.commit()
    return {"userId": str(target.id), "role": membership.role}


@router.delete("/graphs/{graph_ref}/members/{user_ref}", status_code=204)
def delete_member(
    user_ref: str,
    access: GraphAccess = Depends(graph_owner),
    store: GraphStore = Depends(get_store),
) -> None:
    target = _resolve_member_user(store, user_ref)
    membership = store.membership(access.graph.id, target.id)
    if membership is None:
        raise HTTPException(status_code=404, detail="that user is not a member of this graph")
    store.remove_member(membership)
    _ensure_an_owner_remains(store, access, changing_user_id=target.id)
    store.session.commit()


def _ensure_an_owner_remains(store: GraphStore, access: GraphAccess, *, changing_user_id: uuid.UUID) -> None:
    store.session.flush()
    if not any(m.role == "owner" for m in store.members(access.graph.id)):
        raise HTTPException(status_code=409, detail="a graph must keep at least one owner")


@router.get("/share/{token}")
def resolve_share_token(token: str, store: GraphStore = Depends(get_store)) -> dict:
    """Public: resolve a share token to its graph so the share UI can load it."""
    link = store.find_share_token(token)
    if link is None:
        raise HTTPException(status_code=404, detail="share link is invalid or revoked")
    graph = store.get_graph(str(link.graph_id))
    if graph is None:
        raise HTTPException(status_code=404, detail="share link points at a deleted graph")
    return {"graph": _graph_payload(graph)}


# --- share links -------------------------------------------------------------------

@router.get("/graphs/{graph_ref}/share-links")
def list_share_links(
    access: GraphAccess = Depends(graph_owner),
    store: GraphStore = Depends(get_store),
) -> dict:
    return {
        "shareLinks": [
            {
                "id": str(link.id),
                "token": link.token,
                "createdAt": link.created_at.isoformat(),
                "revokedAt": link.revoked_at.isoformat() if link.revoked_at else None,
            }
            for link in store.share_links(access.graph.id)
        ]
    }


@router.post("/graphs/{graph_ref}/share-links", status_code=201)
def create_share_link(
    access: GraphAccess = Depends(graph_owner),
    store: GraphStore = Depends(get_store),
) -> dict:
    link = store.create_share_link(access.graph.id, None)
    store.session.commit()
    return {"id": str(link.id), "token": link.token, "createdAt": link.created_at.isoformat(), "revokedAt": None}


@router.delete("/graphs/{graph_ref}/share-links/{link_id}", status_code=204)
def revoke_share_link(
    link_id: uuid.UUID,
    access: GraphAccess = Depends(graph_owner),
    store: GraphStore = Depends(get_store),
) -> None:
    link = store.get_share_link(link_id)
    if link is None or link.graph_id != access.graph.id:
        raise HTTPException(status_code=404, detail="no such share link on this graph")
    store.revoke_share_link(link)
    store.session.commit()
