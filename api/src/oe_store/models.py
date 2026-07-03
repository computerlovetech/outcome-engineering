"""SQLAlchemy ORM models — the Postgres schema from GOAL.md §3."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    oidc_subject: Mapped[str] = mapped_column(String(255), unique=True)
    email: Mapped[str | None] = mapped_column(String(320))
    name: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Graph(Base):
    __tablename__ = "graphs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    memberships: Mapped[list[GraphMembership]] = relationship(
        back_populates="graph", cascade="all, delete-orphan"
    )


class GraphMembership(Base):
    __tablename__ = "graph_memberships"
    __table_args__ = (UniqueConstraint("graph_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    graph_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("graphs.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(16))  # owner | editor | viewer

    graph: Mapped[Graph] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship()


class ShareLink(Base):
    __tablename__ = "share_links"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    graph_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("graphs.id", ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(String(64), unique=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NodeRow(Base):
    __tablename__ = "nodes"
    __table_args__ = (UniqueConstraint("graph_id", "kind", "slug"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    graph_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("graphs.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(32))
    slug: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(500), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    starts: Mapped[date | None] = mapped_column(Date)  # strategy only
    ends: Mapped[date | None] = mapped_column(Date)  # strategy only
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    icp_refs: Mapped[list[NodeIcpRef]] = relationship(
        back_populates="node",
        cascade="all, delete-orphan",
        foreign_keys="NodeIcpRef.node_id",
    )


class NodeIcpRef(Base):
    __tablename__ = "node_icp_refs"
    __table_args__ = (UniqueConstraint("node_id", "icp_node_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    icp_node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))

    node: Mapped[NodeRow] = relationship(back_populates="icp_refs", foreign_keys=[node_id])


class FlywheelRow(Base):
    __tablename__ = "flywheels"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    graph_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("graphs.id", ondelete="CASCADE"), unique=True)
    slug: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(500), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str | None] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer, default=1)

    nodes: Mapped[list[FlywheelNodeRow]] = relationship(
        back_populates="flywheel", cascade="all, delete-orphan"
    )


class FlywheelNodeRow(Base):
    __tablename__ = "flywheel_nodes"
    __table_args__ = (UniqueConstraint("flywheel_id", "slug"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    flywheel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("flywheels.id", ondelete="CASCADE"))
    slug: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(500), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str | None] = mapped_column(String(64))
    position: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)

    flywheel: Mapped[FlywheelRow] = relationship(back_populates="nodes")


class FlywheelEdge(Base):
    __tablename__ = "flywheel_edges"
    __table_args__ = (UniqueConstraint("from_node_id", "to_node_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    from_node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("flywheel_nodes.id", ondelete="CASCADE"))
    to_node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("flywheel_nodes.id", ondelete="CASCADE"))
