"""GraphStore: the repository between the API and Postgres.

Loads GraphSnapshot objects for oe_core to reason about and applies mutations.
Domain rules are NOT checked here — the API composes oe_core.rules with these
primitives. One store instance wraps one Session; the caller owns commit().
"""

from __future__ import annotations

import secrets
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from oe_core.errors import NotFoundError, VersionConflictError
from oe_core.model import Flywheel, FlywheelNode, GraphSnapshot, Node
from oe_store.models import (
    FlywheelEdge,
    FlywheelNodeRow,
    FlywheelRow,
    Graph,
    GraphMembership,
    NodeIcpRef,
    NodeJobRef,
    NodeRow,
    ShareLink,
    User,
)


class GraphStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    # --- users ---------------------------------------------------------------

    def upsert_user(self, *, oidc_subject: str, email: str | None, name: str | None) -> User:
        user = self.session.scalar(select(User).where(User.oidc_subject == oidc_subject))
        if user is None:
            user = User(oidc_subject=oidc_subject, email=email, name=name)
            self.session.add(user)
            self.session.flush()
        elif (email and user.email != email) or (name and user.name != name):
            user.email = email or user.email
            user.name = name or user.name
        return user

    def get_user(self, user_id: uuid.UUID) -> User | None:
        return self.session.get(User, user_id)

    def find_user_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email))

    # --- graphs ----------------------------------------------------------------

    def graphs_for_user(self, user_id: uuid.UUID) -> list[tuple[Graph, str]]:
        rows = self.session.execute(
            select(Graph, GraphMembership.role)
            .join(GraphMembership, GraphMembership.graph_id == Graph.id)
            .where(GraphMembership.user_id == user_id)
            .order_by(Graph.created_at)
        )
        return [(graph, role) for graph, role in rows]

    def create_graph(self, *, slug: str, name: str, owner_id: uuid.UUID) -> Graph:
        graph = Graph(slug=slug, name=name)
        self.session.add(graph)
        self.session.flush()
        self.session.add(GraphMembership(graph_id=graph.id, user_id=owner_id, role="owner"))
        return graph

    def get_graph(self, graph_ref: str) -> Graph | None:
        try:
            graph_id = uuid.UUID(graph_ref)
        except ValueError:
            return self.session.scalar(select(Graph).where(Graph.slug == graph_ref))
        return self.session.get(Graph, graph_id)

    def graph_slug_taken(self, slug: str) -> bool:
        return self.session.scalar(select(Graph.id).where(Graph.slug == slug)) is not None

    def delete_graph(self, graph: Graph) -> None:
        self.session.delete(graph)

    # --- membership --------------------------------------------------------------

    def membership(self, graph_id: uuid.UUID, user_id: uuid.UUID) -> GraphMembership | None:
        return self.session.scalar(
            select(GraphMembership).where(
                GraphMembership.graph_id == graph_id, GraphMembership.user_id == user_id
            )
        )

    def members(self, graph_id: uuid.UUID) -> list[GraphMembership]:
        return list(
            self.session.scalars(
                select(GraphMembership)
                .options(selectinload(GraphMembership.user))
                .where(GraphMembership.graph_id == graph_id)
            )
        )

    def set_member(self, graph_id: uuid.UUID, user_id: uuid.UUID, role: str) -> GraphMembership:
        existing = self.membership(graph_id, user_id)
        if existing is not None:
            existing.role = role
            return existing
        membership = GraphMembership(graph_id=graph_id, user_id=user_id, role=role)
        self.session.add(membership)
        return membership

    def remove_member(self, membership: GraphMembership) -> None:
        self.session.delete(membership)

    # --- share links ----------------------------------------------------------------

    def share_links(self, graph_id: uuid.UUID) -> list[ShareLink]:
        return list(
            self.session.scalars(
                select(ShareLink).where(ShareLink.graph_id == graph_id).order_by(ShareLink.created_at)
            )
        )

    def create_share_link(self, graph_id: uuid.UUID, created_by: uuid.UUID | None) -> ShareLink:
        link = ShareLink(graph_id=graph_id, token=secrets.token_urlsafe(32), created_by=created_by)
        self.session.add(link)
        self.session.flush()
        return link

    def revoke_share_link(self, link: ShareLink) -> None:
        link.revoked_at = datetime.now(timezone.utc)

    def get_share_link(self, link_id: uuid.UUID) -> ShareLink | None:
        return self.session.get(ShareLink, link_id)

    def find_share_token(self, token: str) -> ShareLink | None:
        return self.session.scalar(
            select(ShareLink).where(ShareLink.token == token, ShareLink.revoked_at.is_(None))
        )

    # --- snapshot ---------------------------------------------------------------------

    def load_snapshot(self, graph_id: uuid.UUID) -> GraphSnapshot:
        rows = list(
            self.session.scalars(
                select(NodeRow)
                .options(selectinload(NodeRow.icp_refs), selectinload(NodeRow.job_refs))
                .where(NodeRow.graph_id == graph_id)
            )
        )
        nodes = [
            Node(
                id=str(row.id),
                kind=row.kind,
                slug=row.slug,
                title=row.title,
                content=row.content,
                parent_id=str(row.parent_id) if row.parent_id else None,
                position=row.position,
                version=row.version,
                icp_ref_ids=tuple(str(ref.icp_node_id) for ref in row.icp_refs),
                job_ref_ids=tuple(str(ref.job_node_id) for ref in row.job_refs),
                starts=row.starts,
                ends=row.ends,
            )
            for row in rows
        ]
        return GraphSnapshot(nodes=nodes, flywheel=self.load_flywheel(graph_id))

    def load_flywheel(self, graph_id: uuid.UUID) -> Flywheel | None:
        row = self.session.scalar(
            select(FlywheelRow)
            .options(selectinload(FlywheelRow.nodes))
            .where(FlywheelRow.graph_id == graph_id)
        )
        if row is None:
            return None
        node_ids = [node.id for node in row.nodes]
        edges = list(
            self.session.scalars(select(FlywheelEdge).where(FlywheelEdge.from_node_id.in_(node_ids)))
        ) if node_ids else []
        next_map: dict[uuid.UUID, list[str]] = {}
        for edge in edges:
            next_map.setdefault(edge.from_node_id, []).append(str(edge.to_node_id))
        return Flywheel(
            id=str(row.id),
            slug=row.slug,
            title=row.title,
            content=row.content,
            status=row.status,
            nodes=tuple(
                FlywheelNode(
                    id=str(node.id),
                    slug=node.slug,
                    title=node.title,
                    content=node.content,
                    status=node.status,
                    position=node.position,
                    next_ids=tuple(next_map.get(node.id, [])),
                )
                for node in sorted(row.nodes, key=lambda n: (n.position, n.slug))
            ),
        )

    # --- nodes -------------------------------------------------------------------------

    def get_node_row(self, node_id: str) -> NodeRow:
        row = self.session.get(NodeRow, uuid.UUID(node_id))
        if row is None:
            raise NotFoundError(f"no node with id {node_id}")
        return row

    def create_node(
        self,
        graph_id: uuid.UUID,
        *,
        kind: str,
        slug: str,
        title: str,
        content: str,
        parent_id: str | None,
        position: int = 0,
        starts: date | None = None,
        ends: date | None = None,
        icp_ref_ids: tuple[str, ...] = (),
        job_ref_ids: tuple[str, ...] = (),
    ) -> NodeRow:
        row = NodeRow(
            graph_id=graph_id,
            kind=kind,
            slug=slug,
            title=title,
            content=content,
            parent_id=uuid.UUID(parent_id) if parent_id else None,
            position=position,
            starts=starts,
            ends=ends,
        )
        self.session.add(row)
        self.session.flush()
        for icp_id in icp_ref_ids:
            self.session.add(NodeIcpRef(node_id=row.id, icp_node_id=uuid.UUID(icp_id)))
        for job_id in job_ref_ids:
            self.session.add(NodeJobRef(node_id=row.id, job_node_id=uuid.UUID(job_id)))
        self.session.flush()
        return row

    def update_node(
        self,
        row: NodeRow,
        *,
        expected_version: int,
        title: str | None = None,
        content: str | None = None,
        position: int | None = None,
        starts: date | None = None,
        ends: date | None = None,
        set_dates: bool = False,
        icp_ref_ids: tuple[str, ...] | None = None,
        job_ref_ids: tuple[str, ...] | None = None,
    ) -> NodeRow:
        if row.version != expected_version:
            raise VersionConflictError(
                f"{row.kind}.{row.slug} was changed by someone else "
                f"(your version {expected_version}, current {row.version}); reload and retry"
            )
        if title is not None:
            row.title = title
        if content is not None:
            row.content = content
        if position is not None:
            row.position = position
        if set_dates:
            row.starts = starts
            row.ends = ends
        if icp_ref_ids is not None:
            row.icp_refs = [NodeIcpRef(node_id=row.id, icp_node_id=uuid.UUID(i)) for i in icp_ref_ids]
        if job_ref_ids is not None:
            row.job_refs = [NodeJobRef(node_id=row.id, job_node_id=uuid.UUID(i)) for i in job_ref_ids]
        row.version += 1
        self.session.flush()
        return row

    def delete_nodes(self, node_ids: list[str]) -> None:
        """Delete nodes given in top-down order (ancestor first in the list);
        deletion runs bottom-up so ON DELETE CASCADE never races the explicit
        deletes."""
        for node_id in reversed(node_ids):
            row = self.session.get(NodeRow, uuid.UUID(node_id))
            if row is not None:
                self.session.delete(row)
                self.session.flush()

    # --- flywheel ------------------------------------------------------------------------

    def get_flywheel_row(self, graph_id: uuid.UUID) -> FlywheelRow | None:
        return self.session.scalar(
            select(FlywheelRow)
            .options(selectinload(FlywheelRow.nodes))
            .where(FlywheelRow.graph_id == graph_id)
        )

    def create_flywheel(self, graph_id: uuid.UUID, *, slug: str, title: str, content: str, status: str | None) -> FlywheelRow:
        row = FlywheelRow(graph_id=graph_id, slug=slug, title=title, content=content, status=status)
        self.session.add(row)
        self.session.flush()
        return row

    def delete_flywheel(self, row: FlywheelRow) -> None:
        node_ids = [node.id for node in row.nodes]
        if node_ids:
            for edge in self.session.scalars(
                select(FlywheelEdge).where(FlywheelEdge.from_node_id.in_(node_ids))
            ):
                self.session.delete(edge)
        self.session.delete(row)

    def get_flywheel_node_row(self, flywheel_id: uuid.UUID, node_id: str) -> FlywheelNodeRow:
        try:
            key = uuid.UUID(node_id)
        except ValueError:
            row = self.session.scalar(
                select(FlywheelNodeRow).where(
                    FlywheelNodeRow.flywheel_id == flywheel_id,
                    FlywheelNodeRow.slug == node_id.removeprefix("flywheel-node."),
                )
            )
        else:
            row = self.session.get(FlywheelNodeRow, key)
        if row is None or row.flywheel_id != flywheel_id:
            raise NotFoundError(f"no flywheel node matches {node_id!r}")
        return row

    def create_flywheel_node(
        self, flywheel_id: uuid.UUID, *, slug: str, title: str, content: str, status: str | None, position: int = 0
    ) -> FlywheelNodeRow:
        row = FlywheelNodeRow(
            flywheel_id=flywheel_id, slug=slug, title=title, content=content, status=status, position=position
        )
        self.session.add(row)
        self.session.flush()
        return row

    def delete_flywheel_node(self, row: FlywheelNodeRow) -> None:
        for edge in self.session.scalars(
            select(FlywheelEdge).where(
                (FlywheelEdge.from_node_id == row.id) | (FlywheelEdge.to_node_id == row.id)
            )
        ):
            self.session.delete(edge)
        self.session.delete(row)

    def set_flywheel_next(self, from_node_id: uuid.UUID, to_node_ids: list[uuid.UUID]) -> None:
        for edge in self.session.scalars(
            select(FlywheelEdge).where(FlywheelEdge.from_node_id == from_node_id)
        ):
            self.session.delete(edge)
        self.session.flush()
        for to_id in to_node_ids:
            self.session.add(FlywheelEdge(from_node_id=from_node_id, to_node_id=to_id))
        self.session.flush()
