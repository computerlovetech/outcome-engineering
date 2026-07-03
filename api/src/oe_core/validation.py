"""Whole-graph validation: reports residual issues the mutation-time rules
cannot fully prevent (or that legacy data might contain)."""

from __future__ import annotations

from oe_core.model import (
    ICP_REFERRING_KINDS,
    GraphSnapshot,
    Node,
    ValidationIssue,
    allowed_child_kinds,
)


def validate_graph(snapshot: GraphSnapshot) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    _check_visions(snapshot, issues)
    _check_placements(snapshot, issues)
    _check_strategies(snapshot, issues)
    _check_icp_refs(snapshot, issues)
    _check_flywheel(snapshot, issues)
    return issues


def _check_visions(snapshot: GraphSnapshot, issues: list[ValidationIssue]) -> None:
    visions = snapshot.of_kind("vision")
    if len(visions) > 1:
        refs = ", ".join(node.ref for node in visions)
        issues.append(ValidationIssue("graph", f"graph has multiple visions: {refs}"))


def _check_placements(snapshot: GraphSnapshot, issues: list[ValidationIssue]) -> None:
    for node in snapshot.nodes:
        parent = snapshot.by_id(node.parent_id) if node.parent_id is not None else None
        parent_kind = parent.kind if parent is not None else "root"
        if node.kind not in allowed_child_kinds(parent_kind):
            location = f"under {parent.ref}" if parent is not None else "at the graph root"
            issues.append(ValidationIssue(node.ref, f"{node.kind} is not allowed {location}"))


def _check_strategies(snapshot: GraphSnapshot, issues: list[ValidationIssue]) -> None:
    periods: list[Node] = []
    for node in snapshot.of_kind("strategy"):
        if node.starts is None or node.ends is None:
            issues.append(ValidationIssue(node.ref, "strategy must declare starts and ends dates"))
            continue
        if node.starts > node.ends:
            issues.append(ValidationIssue(node.ref, "strategy starts must be on or before ends"))
            continue
        periods.append(node)

    ordered = sorted(periods, key=lambda node: (node.starts, node.ends, node.slug))
    for index, current in enumerate(ordered):
        for other in ordered[index + 1 :]:
            if current.starts <= other.ends and other.starts <= current.ends:
                issues.append(
                    ValidationIssue(
                        other.ref,
                        f"strategy period overlaps with {current.ref}: "
                        f"{other.starts.isoformat()}..{other.ends.isoformat()} overlaps "
                        f"{current.starts.isoformat()}..{current.ends.isoformat()}",
                    )
                )


def _check_icp_refs(snapshot: GraphSnapshot, issues: list[ValidationIssue]) -> None:
    for node in snapshot.nodes:
        if node.icp_ref_ids and node.kind not in ICP_REFERRING_KINDS:
            allowed = ", ".join(sorted(ICP_REFERRING_KINDS))
            issues.append(ValidationIssue(node.ref, f"{node.kind} cannot reference ICPs; only {allowed} may"))
            continue
        for icp_id in node.icp_ref_ids:
            target = snapshot.by_id(icp_id)
            if target is None:
                issues.append(ValidationIssue(node.ref, f"icp reference {icp_id!r} does not resolve to a node"))
            elif target.kind != "icp":
                issues.append(ValidationIssue(node.ref, f"icp reference {target.ref} is a {target.kind}, not an icp"))


def _check_flywheel(snapshot: GraphSnapshot, issues: list[ValidationIssue]) -> None:
    flywheel = snapshot.flywheel
    if flywheel is None:
        return
    node_ids = {node.id for node in flywheel.nodes}
    for node in flywheel.nodes:
        if not node.next_ids:
            issues.append(ValidationIssue(node.ref, "flywheel node must declare at least one next step"))
        for next_id in node.next_ids:
            if next_id not in node_ids:
                issues.append(ValidationIssue(node.ref, f"next reference {next_id!r} does not resolve to a flywheel node"))
        if not _has_body(node.content):
            issues.append(ValidationIssue(node.ref, "flywheel node must explain why it creates the next step"))


def _has_body(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines()]
    return any(line and not line.startswith("#") for line in lines)
