"""JSON payload assembly from domain snapshots (parity with the old read.py)."""

from __future__ import annotations

from oe_core.context import context_markdown, flywheel_markdown
from oe_core.model import PARENT_KIND_TO_CHILD_KIND, Flywheel, GraphSnapshot, Node
from oe_core.validation import validate_graph

SUMMARY_KEYS = ("id", "ref", "kind", "slug", "title")


def node_payload(snapshot: GraphSnapshot, node: Node) -> dict:
    by_id = {n.id: n for n in snapshot.nodes}
    return {
        "id": node.id,
        "ref": node.ref,
        "kind": node.kind,
        "slug": node.slug,
        "title": node.title,
        "content": node.content,
        "parent": by_id[node.parent_id].ref if node.parent_id in by_id else None,
        "parentId": node.parent_id,
        "children": [child.ref for child in snapshot.children(node)],
        "icps": [by_id[i].ref for i in node.icp_ref_ids if i in by_id],
        "icpIds": list(node.icp_ref_ids),
        "jobs": [by_id[i].ref for i in node.job_ref_ids if i in by_id],
        "jobIds": list(node.job_ref_ids),
        "position": node.position,
        "version": node.version,
        "starts": node.starts.isoformat() if node.starts else None,
        "ends": node.ends.isoformat() if node.ends else None,
    }


def node_summary(snapshot: GraphSnapshot, node: Node) -> dict:
    payload = node_payload(snapshot, node)
    return {key: payload[key] for key in SUMMARY_KEYS}


def nodes_payload(snapshot: GraphSnapshot, kind: str | None = None) -> dict:
    nodes = snapshot.nodes if kind is None else snapshot.of_kind(kind)
    ordered = sorted(nodes, key=lambda n: (n.kind, n.slug))
    return {"nodes": [node_payload(snapshot, node) for node in ordered]}


def tree_payload(snapshot: GraphSnapshot) -> dict:
    def subtree(node: Node) -> dict:
        return {
            **node_summary(snapshot, node),
            "children": [subtree(child) for child in snapshot.children(node)],
        }

    return {"roots": [subtree(node) for node in snapshot.children(None)]}


def trace_payload(snapshot: GraphSnapshot, node: Node) -> dict:
    ancestors = snapshot.ancestors(node)
    return {
        "node": node_payload(snapshot, node),
        "trace": [node_summary(snapshot, n) for n in [*ancestors, node]],
        "children": [node_summary(snapshot, child) for child in snapshot.children(node)],
    }


def context_payload(snapshot: GraphSnapshot, node: Node) -> dict:
    ancestors = snapshot.ancestors(node)
    icps = snapshot.related_icps(node)
    jobs = snapshot.related_jobs(node)
    return {
        "node": node_payload(snapshot, node),
        "trace": [node_summary(snapshot, n) for n in [*ancestors, node]],
        "ancestors": [node_payload(snapshot, n) for n in ancestors],
        "icps": [node_payload(snapshot, icp) for icp in icps],
        "jobs": [node_payload(snapshot, job) for job in jobs],
        "children": [node_summary(snapshot, child) for child in snapshot.children(node)],
        "flywheelContext": flywheel_markdown(snapshot.flywheel) if snapshot.flywheel else "",
        "markdown": context_markdown(snapshot, node),
    }


def validation_payload(snapshot: GraphSnapshot) -> dict:
    issues = validate_graph(snapshot)
    return {
        "valid": not any(issue.severity == "error" for issue in issues),
        "issues": [
            {"ref": issue.ref, "message": issue.message, "severity": issue.severity} for issue in issues
        ],
    }


def flywheel_payload(flywheel: Flywheel | None) -> dict | None:
    if flywheel is None:
        return None
    by_id = {node.id: node for node in flywheel.nodes}
    return {
        "id": flywheel.id,
        "ref": flywheel.ref,
        "slug": flywheel.slug,
        "title": flywheel.title,
        "status": flywheel.status,
        "content": flywheel.content,
        "nodes": [
            {
                "id": node.id,
                "ref": node.ref,
                "slug": node.slug,
                "title": node.title,
                "status": node.status,
                "content": node.content,
                "position": node.position,
                "next": [by_id[i].ref for i in node.next_ids if i in by_id],
                "nextIds": list(node.next_ids),
            }
            for node in flywheel.nodes
        ],
    }


def graph_overview_payload(snapshot: GraphSnapshot, *, read_only: bool) -> dict:
    """Everything the graph canvas needs in one call."""
    nodes = []
    edges = []
    icp_served_by: dict[str, list[str]] = {}
    job_served_by: dict[str, list[str]] = {}
    for node in snapshot.nodes:
        payload = node_payload(snapshot, node)
        payload["deletable"] = not read_only
        nodes.append(payload)
        if payload["parent"] is not None:
            edges.append({"source": payload["parent"], "target": node.ref, "type": "structural"})
        for icp_ref in payload["icps"]:
            edges.append({"source": node.ref, "target": icp_ref, "type": "icp"})
            icp_served_by.setdefault(icp_ref, []).append(node.ref)
        for job_ref in payload["jobs"]:
            edges.append({"source": node.ref, "target": job_ref, "type": "job"})
            job_served_by.setdefault(job_ref, []).append(node.ref)
    for payload in nodes:
        if payload["kind"] == "icp":
            payload["servedBy"] = icp_served_by.get(payload["ref"], [])
        elif payload["kind"] == "job":
            payload["servedBy"] = job_served_by.get(payload["ref"], [])

    vision = snapshot.vision()
    strategy = snapshot.current_strategy()
    return {
        "readOnly": read_only,
        "vision": vision.content if vision else "",
        "strategy": strategy.content if strategy else "",
        "flywheel": flywheel_payload(snapshot.flywheel),
        "schema": {
            "childKinds": {parent: sorted(children) for parent, children in PARENT_KIND_TO_CHILD_KIND.items()}
        },
        "nodes": nodes,
        "edges": edges,
    }
