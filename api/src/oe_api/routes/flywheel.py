from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from oe_api import serialize
from oe_api.authz import GraphAccess, graph_editor, graph_viewer
from oe_api.db import get_store
from oe_api.schemas import FlywheelNodeCreate, FlywheelNodePatch, FlywheelPut
from oe_core.model import valid_slug
from oe_store.models import FlywheelNodeRow, FlywheelRow
from oe_store.store import GraphStore

router = APIRouter()


def _require_flywheel(store: GraphStore, graph_id: uuid.UUID) -> FlywheelRow:
    row = store.get_flywheel_row(graph_id)
    if row is None:
        raise HTTPException(status_code=404, detail="this graph has no flywheel yet")
    return row


def _check_slug(slug: str) -> None:
    if not valid_slug(slug):
        raise HTTPException(status_code=400, detail=f"invalid slug {slug!r}; use lowercase letters, digits, and single hyphens")


def _resolve_next_ids(store: GraphStore, flywheel: FlywheelRow, selectors: list[str], *, exclude: FlywheelNodeRow | None = None) -> list[uuid.UUID]:
    return [store.get_flywheel_node_row(flywheel.id, sel).id for sel in selectors]


@router.get("/graphs/{graph_ref}/flywheel")
def get_flywheel(
    access: GraphAccess = Depends(graph_viewer),
    store: GraphStore = Depends(get_store),
) -> dict:
    return {"flywheel": serialize.flywheel_payload(store.load_flywheel(access.graph.id))}


@router.put("/graphs/{graph_ref}/flywheel")
def put_flywheel(
    body: FlywheelPut,
    access: GraphAccess = Depends(graph_editor),
    store: GraphStore = Depends(get_store),
) -> dict:
    _check_slug(body.slug)
    row = store.get_flywheel_row(access.graph.id)
    if row is None:
        store.create_flywheel(access.graph.id, slug=body.slug, title=body.title, content=body.content, status=body.status)
    else:
        row.slug = body.slug
        row.title = body.title
        row.content = body.content
        row.status = body.status
    store.session.commit()
    return {"flywheel": serialize.flywheel_payload(store.load_flywheel(access.graph.id))}


@router.delete("/graphs/{graph_ref}/flywheel", status_code=204)
def delete_flywheel(
    access: GraphAccess = Depends(graph_editor),
    store: GraphStore = Depends(get_store),
) -> None:
    store.delete_flywheel(_require_flywheel(store, access.graph.id))
    store.session.commit()


@router.post("/graphs/{graph_ref}/flywheel/nodes", status_code=201)
def create_flywheel_node(
    body: FlywheelNodeCreate,
    access: GraphAccess = Depends(graph_editor),
    store: GraphStore = Depends(get_store),
) -> dict:
    flywheel = _require_flywheel(store, access.graph.id)
    _check_slug(body.slug)
    if any(node.slug == body.slug for node in flywheel.nodes):
        raise HTTPException(status_code=409, detail=f"a flywheel node with slug {body.slug!r} already exists")
    row = store.create_flywheel_node(
        flywheel.id,
        slug=body.slug,
        title=body.title or body.slug.replace("-", " ").title(),
        content=body.content,
        status=body.status,
        position=body.position,
    )
    if body.next:
        store.set_flywheel_next(row.id, _resolve_next_ids(store, flywheel, body.next))
    store.session.commit()
    return {"flywheel": serialize.flywheel_payload(store.load_flywheel(access.graph.id))}


@router.patch("/graphs/{graph_ref}/flywheel/nodes/{node_selector}")
def patch_flywheel_node(
    node_selector: str,
    body: FlywheelNodePatch,
    access: GraphAccess = Depends(graph_editor),
    store: GraphStore = Depends(get_store),
) -> dict:
    flywheel = _require_flywheel(store, access.graph.id)
    row = store.get_flywheel_node_row(flywheel.id, node_selector)
    if body.title is not None:
        row.title = body.title
    if body.content is not None:
        row.content = body.content
    if body.status is not None:
        row.status = body.status or None
    if body.position is not None:
        row.position = body.position
    if body.next is not None:
        store.set_flywheel_next(row.id, _resolve_next_ids(store, flywheel, body.next))
    store.session.commit()
    return {"flywheel": serialize.flywheel_payload(store.load_flywheel(access.graph.id))}


@router.delete("/graphs/{graph_ref}/flywheel/nodes/{node_selector}", status_code=204)
def delete_flywheel_node(
    node_selector: str,
    access: GraphAccess = Depends(graph_editor),
    store: GraphStore = Depends(get_store),
) -> None:
    flywheel = _require_flywheel(store, access.graph.id)
    store.delete_flywheel_node(store.get_flywheel_node_row(flywheel.id, node_selector))
    store.session.commit()
