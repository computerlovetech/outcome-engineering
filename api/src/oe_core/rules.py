"""Mutation-time rules: everything the API must check before writing a node.

The filesystem version validated the whole tree after the fact; here the rules
run per mutation against the current snapshot, so invalid states are rejected
up front. `validation.validate_graph` reports the residual cross-node issues.
"""

from __future__ import annotations

from datetime import date

from oe_core.errors import (
    CascadeRequiredError,
    DomainError,
    IcpReferenceError,
    JobReferenceError,
    PlacementError,
    SlugError,
    StrategyDateError,
)
from oe_core.model import (
    ICP_REFERRING_KINDS,
    JOB_REFERRING_KINDS,
    NODE_KINDS,
    GraphSnapshot,
    Node,
    allowed_child_kinds,
    valid_slug,
)


def check_create(
    snapshot: GraphSnapshot,
    *,
    kind: str,
    slug: str,
    parent: Node | None,
    starts: date | None = None,
    ends: date | None = None,
    icp_ref_ids: tuple[str, ...] = (),
    job_ref_ids: tuple[str, ...] = (),
) -> None:
    """Raise a DomainError if creating this node would violate the model."""
    if kind not in NODE_KINDS:
        raise PlacementError(f"unknown node kind {kind!r}; expected one of {', '.join(NODE_KINDS)}")

    parent_kind = parent.kind if parent is not None else "root"
    allowed = allowed_child_kinds(parent_kind)
    if kind not in allowed:
        location = f"under {parent.ref}" if parent is not None else "at the graph root"
        allowed_text = ", ".join(sorted(allowed)) if allowed else "nothing"
        raise PlacementError(f"{kind} is not allowed {location}; allowed: {allowed_text}")

    check_slug(snapshot, kind=kind, slug=slug)

    if kind == "vision" and snapshot.vision() is not None:
        raise PlacementError("graph already has a vision; edit it instead of adding another")

    if kind == "strategy":
        check_strategy_dates(snapshot, starts=starts, ends=ends)
    elif starts is not None or ends is not None:
        raise StrategyDateError(f"{kind} cannot declare starts/ends; only strategy nodes have a period")

    check_icp_refs(snapshot, kind=kind, icp_ref_ids=icp_ref_ids)
    check_job_refs(snapshot, kind=kind, job_ref_ids=job_ref_ids)


def check_slug(snapshot: GraphSnapshot, *, kind: str, slug: str) -> None:
    if not valid_slug(slug):
        raise SlugError(f"invalid slug {slug!r}; use lowercase letters, digits, and single hyphens")
    if any(node.kind == kind and node.slug == slug for node in snapshot.nodes):
        raise SlugError(f"a {kind} with slug {slug!r} already exists in this graph")


def check_strategy_dates(
    snapshot: GraphSnapshot,
    *,
    starts: date | None,
    ends: date | None,
    exclude_node_id: str | None = None,
) -> None:
    if starts is None or ends is None:
        raise StrategyDateError("strategy must declare starts and ends dates (YYYY-MM-DD)")
    if starts > ends:
        raise StrategyDateError("strategy starts must be on or before ends")
    for other in snapshot.of_kind("strategy"):
        if other.id == exclude_node_id or other.starts is None or other.ends is None:
            continue
        if starts <= other.ends and other.starts <= ends:
            raise StrategyDateError(
                f"strategy period {starts.isoformat()}..{ends.isoformat()} overlaps "
                f"{other.ref} ({other.starts.isoformat()}..{other.ends.isoformat()})"
            )


def check_icp_refs(snapshot: GraphSnapshot, *, kind: str, icp_ref_ids: tuple[str, ...]) -> None:
    _check_refs(
        snapshot, kind=kind, ref_ids=icp_ref_ids, target_kind="icp",
        referring_kinds=ICP_REFERRING_KINDS, error=IcpReferenceError, label="ICPs", article="an icp",
    )


def check_job_refs(snapshot: GraphSnapshot, *, kind: str, job_ref_ids: tuple[str, ...]) -> None:
    _check_refs(
        snapshot, kind=kind, ref_ids=job_ref_ids, target_kind="job",
        referring_kinds=JOB_REFERRING_KINDS, error=JobReferenceError, label="jobs", article="a job",
    )


def _check_refs(
    snapshot: GraphSnapshot,
    *,
    kind: str,
    ref_ids: tuple[str, ...],
    target_kind: str,
    referring_kinds: set[str],
    error: type[DomainError],
    label: str,
    article: str,
) -> None:
    if not ref_ids:
        return
    if kind not in referring_kinds:
        allowed = ", ".join(sorted(referring_kinds))
        raise error(f"{kind} cannot reference {label}; only {allowed} may")
    for ref_id in ref_ids:
        target = snapshot.by_id(ref_id)
        if target is None:
            raise error(f"{target_kind} reference {ref_id!r} does not resolve to a node in this graph")
        if target.kind != target_kind:
            raise error(f"{target_kind} reference {target.ref} is a {target.kind}, not {article}")


def check_delete(snapshot: GraphSnapshot, node: Node, *, cascade: bool) -> list[Node]:
    """Return the descendants that will be deleted along with the node."""
    descendants = snapshot.descendants(node)
    if descendants and not cascade:
        refs = ", ".join(child.ref for child in descendants[:5])
        suffix = ", ..." if len(descendants) > 5 else ""
        raise CascadeRequiredError(
            f"{node.ref} has {len(descendants)} descendant(s) ({refs}{suffix}); pass cascade=true to delete them too"
        )
    if node.kind in ("icp", "job"):
        referrers = [
            n
            for n in snapshot.nodes
            if node.id in (*n.icp_ref_ids, *n.job_ref_ids) and n not in descendants and n.id != node.id
        ]
        if referrers:
            refs = ", ".join(n.ref for n in referrers[:5])
            raise CascadeRequiredError(f"{node.ref} is referenced by {refs}; remove those references first")
    return descendants
