"""Pure domain model for the product graph.

Storage-agnostic: everything here operates on in-memory snapshot objects.
The API layer loads a GraphSnapshot from Postgres via oe_store and hands it
to these functions; nothing in oe_core may import storage or web code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

NODE_KINDS = (
    "vision",
    "strategy",
    "icp",
    "outcome",
    "opportunity",
    "solution",
    "assumption-test",
    "prd",
)

# Kinds that live at the graph root (parent_id NULL).
ROOT_KINDS = {"vision", "strategy", "icp", "outcome"}

# parent kind -> allowed child kinds. "root" is the graph root itself.
PARENT_KIND_TO_CHILD_KIND: dict[str, set[str]] = {
    "root": {"vision", "strategy", "icp", "outcome"},
    "vision": set(),
    "strategy": set(),
    "icp": set(),
    "outcome": {"opportunity"},
    "opportunity": {"opportunity", "solution"},
    "solution": {"assumption-test", "prd"},
    "assumption-test": set(),
    "prd": set(),
}

# Kinds allowed to reference ICPs (many-to-many, not part of the trace chain).
ICP_REFERRING_KINDS = {"outcome", "opportunity"}

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

FLYWHEEL_NODE_KIND = "flywheel-node"
FLYWHEEL_KIND = "flywheel"


@dataclass(frozen=True)
class Node:
    """A product graph node as the domain sees it."""

    id: str  # uuid string — the real identity
    kind: str
    slug: str
    title: str
    content: str  # free-form markdown
    parent_id: str | None
    position: int = 0
    version: int = 1
    icp_ref_ids: tuple[str, ...] = ()  # node uuids of referenced ICPs
    starts: date | None = None  # strategy only
    ends: date | None = None  # strategy only

    @property
    def ref(self) -> str:
        """Human-facing id, unique per graph."""
        return f"{self.kind}.{self.slug}"


@dataclass(frozen=True)
class FlywheelNode:
    id: str
    slug: str
    title: str
    content: str
    status: str | None
    position: int
    next_ids: tuple[str, ...] = ()  # flywheel node uuids

    @property
    def ref(self) -> str:
        return f"{FLYWHEEL_NODE_KIND}.{self.slug}"


@dataclass(frozen=True)
class Flywheel:
    id: str
    slug: str
    title: str
    content: str
    status: str | None
    nodes: tuple[FlywheelNode, ...] = ()

    @property
    def ref(self) -> str:
        return f"{FLYWHEEL_KIND}.{self.slug}"


@dataclass(frozen=True)
class ValidationIssue:
    ref: str  # human-facing node ref (or "graph" for graph-level issues)
    message: str


@dataclass
class GraphSnapshot:
    """In-memory view of one graph's nodes and flywheel."""

    nodes: list[Node] = field(default_factory=list)
    flywheel: Flywheel | None = None

    def __post_init__(self) -> None:
        self._by_id = {node.id: node for node in self.nodes}
        self._children: dict[str | None, list[Node]] = {}
        for node in sorted(self.nodes, key=lambda n: (n.position, n.slug)):
            self._children.setdefault(node.parent_id, []).append(node)

    def by_id(self, node_id: str) -> Node | None:
        return self._by_id.get(node_id)

    def children(self, node: Node | None) -> list[Node]:
        return self._children.get(node.id if node is not None else None, [])

    def ancestors(self, node: Node) -> list[Node]:
        """Ancestor chain from the root down to (excluding) the node."""
        chain: list[Node] = []
        current = node
        while current.parent_id is not None:
            parent = self._by_id.get(current.parent_id)
            if parent is None:
                break
            chain.append(parent)
            current = parent
        chain.reverse()
        return chain

    def descendants(self, node: Node) -> list[Node]:
        result: list[Node] = []
        stack = list(self.children(node))
        while stack:
            current = stack.pop(0)
            result.append(current)
            stack.extend(self.children(current))
        return result

    def of_kind(self, kind: str) -> list[Node]:
        return [node for node in self.nodes if node.kind == kind]

    def vision(self) -> Node | None:
        visions = self.of_kind("vision")
        return visions[0] if visions else None

    def current_strategy(self, today: date | None = None) -> Node | None:
        """The strategy whose starts..ends period covers today, if any."""
        today = today or date.today()
        for node in self.of_kind("strategy"):
            if node.starts is not None and node.ends is not None and node.starts <= today <= node.ends:
                return node
        return None

    def related_icps(self, node: Node) -> list[Node]:
        """The node's own ICP references plus its ancestors', deduped in order."""
        seen: set[str] = set()
        icps: list[Node] = []
        for candidate in [*self.ancestors(node), node]:
            for icp_id in candidate.icp_ref_ids:
                icp = self._by_id.get(icp_id)
                if icp is not None and icp.kind == "icp" and icp.id not in seen:
                    seen.add(icp.id)
                    icps.append(icp)
        return icps


def allowed_child_kinds(parent_kind: str) -> set[str]:
    """Child kinds the model allows under a parent kind ('root' for the graph root)."""
    return PARENT_KIND_TO_CHILD_KIND.get(parent_kind, set())


def valid_slug(slug: str) -> bool:
    return bool(SLUG_PATTERN.match(slug))
