"""GraphStore tests against an in-memory SQLite DB (schema from the ORM
metadata; Postgres is the production target, exercised via compose)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from oe_core import rules, selector
from oe_core.errors import VersionConflictError
from oe_store.models import Base
from oe_store.store import GraphStore


@pytest.fixture
def store():
    engine = create_engine("sqlite://")
    event.listen(engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield GraphStore(session)


@pytest.fixture
def graph(store):
    user = store.upsert_user(oidc_subject="sub-1", email="user@example.com", name="Test User")
    return store.create_graph(slug="acme", name="Acme", owner_id=user.id)


def test_upsert_user_is_idempotent(store):
    a = store.upsert_user(oidc_subject="s", email="a@x.dk", name="A")
    b = store.upsert_user(oidc_subject="s", email="b@x.dk", name="B")
    assert a.id == b.id
    assert b.email == "b@x.dk"


def test_create_graph_adds_owner_membership(store, graph):
    members = store.members(graph.id)
    assert len(members) == 1
    assert members[0].role == "owner"
    user_graphs = store.graphs_for_user(members[0].user_id)
    assert [(g.slug, role) for g, role in user_graphs] == [("acme", "owner")]


def test_get_graph_by_slug_and_uuid(store, graph):
    assert store.get_graph("acme").id == graph.id
    assert store.get_graph(str(graph.id)).id == graph.id
    assert store.get_graph("nope") is None


def test_snapshot_roundtrip_with_icp_refs(store, graph):
    icp = store.create_node(graph.id, kind="icp", slug="devs", title="Devs", content="c", parent_id=None)
    outcome = store.create_node(
        graph.id, kind="outcome", slug="adoption", title="Adoption", content="c",
        parent_id=None, icp_ref_ids=(str(icp.id),),
    )
    store.create_node(graph.id, kind="opportunity", slug="docs", title="Docs", content="c", parent_id=str(outcome.id))
    snap = store.load_snapshot(graph.id)
    node = selector.resolve(snap, "outcome.adoption")
    assert node.icp_ref_ids == (str(icp.id),)
    assert [c.ref for c in snap.children(node)] == ["opportunity.docs"]
    assert snap.related_icps(selector.resolve(snap, "opportunity.docs"))[0].ref == "icp.devs"


def test_snapshot_roundtrip_with_job_refs(store, graph):
    icp = store.create_node(graph.id, kind="icp", slug="devs", title="Devs", content="c", parent_id=None)
    job = store.create_node(
        graph.id, kind="job", slug="ship-fast", title="Ship fast", content="c",
        parent_id=None, icp_ref_ids=(str(icp.id),),
    )
    outcome = store.create_node(
        graph.id, kind="outcome", slug="adoption", title="Adoption", content="c",
        parent_id=None, job_ref_ids=(str(job.id),),
    )
    store.create_node(graph.id, kind="opportunity", slug="docs", title="Docs", content="c", parent_id=str(outcome.id))
    snap = store.load_snapshot(graph.id)
    node = selector.resolve(snap, "outcome.adoption")
    assert node.job_ref_ids == (str(job.id),)
    assert selector.resolve(snap, "job.ship-fast").icp_ref_ids == (str(icp.id),)
    assert snap.related_jobs(selector.resolve(snap, "opportunity.docs"))[0].ref == "job.ship-fast"

    row = store.get_node_row(node.id)
    store.update_node(row, expected_version=1, job_ref_ids=())
    snap = store.load_snapshot(graph.id)
    assert selector.resolve(snap, "outcome.adoption").job_ref_ids == ()


def test_update_node_version_conflict(store, graph):
    row = store.create_node(graph.id, kind="outcome", slug="o", title="O", content="v1", parent_id=None)
    store.update_node(row, expected_version=1, content="v2")
    assert row.version == 2
    with pytest.raises(VersionConflictError, match="reload and retry"):
        store.update_node(row, expected_version=1, content="v3")
    assert row.content == "v2"


def test_delete_cascade_flow(store, graph):
    outcome = store.create_node(graph.id, kind="outcome", slug="o", title="O", content="", parent_id=None)
    store.create_node(graph.id, kind="opportunity", slug="p", title="P", content="", parent_id=str(outcome.id))
    snap = store.load_snapshot(graph.id)
    node = selector.resolve(snap, "outcome.o")
    descendants = rules.check_delete(snap, node, cascade=True)
    store.delete_nodes([node.id] + [d.id for d in descendants])
    store.session.flush()
    assert store.load_snapshot(graph.id).nodes == []


def test_share_link_lifecycle(store, graph):
    members = store.members(graph.id)
    link = store.create_share_link(graph.id, members[0].user_id)
    assert store.find_share_token(link.token).id == link.id
    store.revoke_share_link(link)
    assert store.find_share_token(link.token) is None


def test_flywheel_roundtrip(store, graph):
    fw = store.create_flywheel(graph.id, slug="loop", title="Loop", content="body", status=None)
    a = store.create_flywheel_node(fw.id, slug="ship", title="Ship", content="why", status="active", position=0)
    b = store.create_flywheel_node(fw.id, slug="learn", title="Learn", content="why", status=None, position=1)
    store.set_flywheel_next(a.id, [b.id])
    store.set_flywheel_next(b.id, [a.id])
    loaded = store.load_flywheel(graph.id)
    assert [n.slug for n in loaded.nodes] == ["ship", "learn"]
    ship = loaded.nodes[0]
    assert ship.next_ids == (str(b.id),)
    # re-pointing replaces edges
    store.set_flywheel_next(a.id, [a.id])
    assert store.load_flywheel(graph.id).nodes[0].next_ids == (str(a.id),)


def test_membership_set_and_remove(store, graph):
    other = store.upsert_user(oidc_subject="sub-2", email="o@x.dk", name="Other")
    store.set_member(graph.id, other.id, "viewer")
    assert store.membership(graph.id, other.id).role == "viewer"
    store.set_member(graph.id, other.id, "editor")
    assert store.membership(graph.id, other.id).role == "editor"
    store.remove_member(store.membership(graph.id, other.id))
    store.session.flush()
    assert store.membership(graph.id, other.id) is None
