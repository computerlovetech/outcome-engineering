"""Selector resolution: `<kind>.<slug>`, bare slug (must be unique), or uuid."""

from __future__ import annotations

import uuid

from oe_core.errors import AmbiguousSelectorError, NotFoundError
from oe_core.model import NODE_KINDS, GraphSnapshot, Node


def resolve(snapshot: GraphSnapshot, selector: str) -> Node:
    selector = selector.strip()
    if not selector:
        raise NotFoundError("empty selector")

    if _is_uuid(selector):
        node = snapshot.by_id(selector)
        if node is None:
            raise NotFoundError(f"no node with id {selector}")
        return node

    if "." in selector:
        kind, _, slug = selector.partition(".")
        if kind not in NODE_KINDS:
            raise NotFoundError(f"unknown node kind {kind!r} in selector {selector!r}")
        for node in snapshot.nodes:
            if node.kind == kind and node.slug == slug:
                return node
        raise NotFoundError(f"no node matches {selector!r}")

    matches = [node for node in snapshot.nodes if node.slug == selector]
    if not matches:
        raise NotFoundError(f"no node matches slug {selector!r}")
    if len(matches) > 1:
        refs = ", ".join(sorted(node.ref for node in matches))
        raise AmbiguousSelectorError(f"slug {selector!r} is ambiguous; matches {refs}")
    return matches[0]


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True
