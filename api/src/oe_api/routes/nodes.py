from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from oe_api import serialize
from oe_api.authz import GraphAccess, graph_editor, graph_viewer
from oe_api.db import get_store
from oe_api.schemas import NodeCreate, NodePatch
from oe_core import rules, selector
from oe_core.errors import DomainError, IcpReferenceError, JobReferenceError, StrategyDateError
from oe_core.model import GraphSnapshot, Node
from oe_store.store import GraphStore

router = APIRouter()


def _resolve_ref_ids(
    snapshot: GraphSnapshot, selectors: list[str], *, kind: str, error: type[DomainError]
) -> tuple[str, ...]:
    ids = []
    for sel in selectors:
        try:
            node = selector.resolve(snapshot, sel)
        except Exception as exc:
            raise error(f"{kind} reference {sel!r} does not resolve to a node in this graph") from exc
        ids.append(node.id)
    return tuple(ids)


def _resolve_icp_ids(snapshot: GraphSnapshot, icp_selectors: list[str]) -> tuple[str, ...]:
    return _resolve_ref_ids(snapshot, icp_selectors, kind="icp", error=IcpReferenceError)


def _resolve_job_ids(snapshot: GraphSnapshot, job_selectors: list[str]) -> tuple[str, ...]:
    return _resolve_ref_ids(snapshot, job_selectors, kind="job", error=JobReferenceError)


@router.get("/graphs/{graph_ref}/nodes")
def list_nodes(
    kind: str | None = Query(default=None),
    access: GraphAccess = Depends(graph_viewer),
    store: GraphStore = Depends(get_store),
) -> dict:
    return serialize.nodes_payload(store.load_snapshot(access.graph.id), kind)


@router.post("/graphs/{graph_ref}/nodes", status_code=201)
def create_node(
    body: NodeCreate,
    access: GraphAccess = Depends(graph_editor),
    store: GraphStore = Depends(get_store),
) -> dict:
    snapshot = store.load_snapshot(access.graph.id)
    parent: Node | None = None
    if body.under is not None:
        parent = selector.resolve(snapshot, body.under)
    icp_ids = _resolve_icp_ids(snapshot, body.icps)
    job_ids = _resolve_job_ids(snapshot, body.jobs)
    rules.check_create(
        snapshot,
        kind=body.kind,
        slug=body.slug,
        parent=parent,
        starts=body.starts,
        ends=body.ends,
        icp_ref_ids=icp_ids,
        job_ref_ids=job_ids,
    )
    title = body.title or body.slug.replace("-", " ").title()
    content = body.content or f"# {title}\n"
    row = store.create_node(
        access.graph.id,
        kind=body.kind,
        slug=body.slug,
        title=title,
        content=content,
        parent_id=parent.id if parent else None,
        position=body.position,
        starts=body.starts,
        ends=body.ends,
        icp_ref_ids=icp_ids,
        job_ref_ids=job_ids,
    )
    store.session.commit()
    snapshot = store.load_snapshot(access.graph.id)
    return {"node": serialize.node_payload(snapshot, selector.resolve(snapshot, str(row.id)))}


@router.get("/graphs/{graph_ref}/nodes/{node_selector}")
def get_node(
    node_selector: str,
    access: GraphAccess = Depends(graph_viewer),
    store: GraphStore = Depends(get_store),
) -> dict:
    snapshot = store.load_snapshot(access.graph.id)
    return {"node": serialize.node_payload(snapshot, selector.resolve(snapshot, node_selector))}


@router.patch("/graphs/{graph_ref}/nodes/{node_selector}")
def patch_node(
    node_selector: str,
    body: NodePatch,
    access: GraphAccess = Depends(graph_editor),
    store: GraphStore = Depends(get_store),
) -> dict:
    snapshot = store.load_snapshot(access.graph.id)
    node = selector.resolve(snapshot, node_selector)

    dates_given = body.starts is not None or body.ends is not None
    if dates_given and node.kind != "strategy":
        raise StrategyDateError(f"{node.kind} cannot declare starts/ends; only strategy nodes have a period")
    set_dates = dates_given
    starts = ends = None
    if dates_given:
        starts = body.starts if body.starts is not None else node.starts
        ends = body.ends if body.ends is not None else node.ends
        rules.check_strategy_dates(snapshot, starts=starts, ends=ends, exclude_node_id=node.id)

    icp_ids = None
    if body.icps is not None:
        icp_ids = _resolve_icp_ids(snapshot, body.icps)
        rules.check_icp_refs(snapshot, kind=node.kind, icp_ref_ids=icp_ids)

    job_ids = None
    if body.jobs is not None:
        job_ids = _resolve_job_ids(snapshot, body.jobs)
        rules.check_job_refs(snapshot, kind=node.kind, job_ref_ids=job_ids)

    row = store.get_node_row(node.id)
    store.update_node(
        row,
        expected_version=body.version,
        title=body.title,
        content=body.content,
        position=body.position,
        starts=starts,
        ends=ends,
        set_dates=set_dates,
        icp_ref_ids=icp_ids,
        job_ref_ids=job_ids,
    )
    store.session.commit()
    snapshot = store.load_snapshot(access.graph.id)
    return {"node": serialize.node_payload(snapshot, selector.resolve(snapshot, node.id))}


@router.delete("/graphs/{graph_ref}/nodes/{node_selector}")
def delete_node(
    node_selector: str,
    cascade: bool = Query(default=False),
    access: GraphAccess = Depends(graph_editor),
    store: GraphStore = Depends(get_store),
) -> dict:
    snapshot = store.load_snapshot(access.graph.id)
    node = selector.resolve(snapshot, node_selector)
    descendants = rules.check_delete(snapshot, node, cascade=cascade)
    store.delete_nodes([node.id] + [d.id for d in descendants])
    store.session.commit()
    return {"deleted": [d.ref for d in [*descendants, node]]}


@router.get("/graphs/{graph_ref}/nodes/{node_selector}/trace")
def trace_node(
    node_selector: str,
    access: GraphAccess = Depends(graph_viewer),
    store: GraphStore = Depends(get_store),
) -> dict:
    snapshot = store.load_snapshot(access.graph.id)
    return serialize.trace_payload(snapshot, selector.resolve(snapshot, node_selector))


@router.get("/graphs/{graph_ref}/nodes/{node_selector}/context")
def context_node(
    node_selector: str,
    access: GraphAccess = Depends(graph_viewer),
    store: GraphStore = Depends(get_store),
) -> dict:
    snapshot = store.load_snapshot(access.graph.id)
    return serialize.context_payload(snapshot, selector.resolve(snapshot, node_selector))
