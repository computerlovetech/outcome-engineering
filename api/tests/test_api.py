"""API tests: httpx TestClient against a per-test SQLite DB, simulation auth.

Simulation mode maps each bearer token to its own dev user, so roles and the
two-session conflict scenario are exercised with different tokens.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

from oe_api.app import create_app
from oe_api.settings import Settings
from oe_store.models import Base
from sqlalchemy.orm import sessionmaker

OWNER = {"Authorization": "Bearer owner"}
EDITOR = {"Authorization": "Bearer editor"}
VIEWER = {"Authorization": "Bearer viewer"}
STRANGER = {"Authorization": "Bearer stranger"}


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    event.listen(engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    settings = Settings(auth_mode="simulation", run_migrations_on_startup=False, database_url="sqlite://")
    app = create_app(settings)
    app.state.session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def graph(client):
    response = client.post("/api/graphs", json={"slug": "acme", "name": "Acme"}, headers=OWNER)
    assert response.status_code == 201, response.text
    # register the other users and add them as members
    client.get("/api/me", headers=EDITOR)
    client.get("/api/me", headers=VIEWER)
    assert client.put("/api/graphs/acme/members/editor@simulated.local", json={"role": "editor"}, headers=OWNER).status_code == 200
    assert client.put("/api/graphs/acme/members/viewer@simulated.local", json={"role": "viewer"}, headers=OWNER).status_code == 200
    return response.json()


def create_node(client, payload, headers=OWNER, expect=201):
    response = client.post("/api/graphs/acme/nodes", json=payload, headers=headers)
    assert response.status_code == expect, response.text
    return response.json()


# --- basics ---------------------------------------------------------------------

def test_health_needs_no_auth(client):
    assert client.get("/api/system/health").json() == {"status": "ok"}


def test_me_requires_auth(client):
    assert client.get("/api/me").status_code == 401
    body = client.get("/api/me", headers=OWNER).json()
    assert body["email"] == "owner@simulated.local"


def test_graph_crud_and_membership_listing(client, graph):
    graphs = client.get("/api/graphs", headers=OWNER).json()["graphs"]
    assert [(g["slug"], g["role"]) for g in graphs] == [("acme", "owner")]
    assert client.get("/api/graphs", headers=STRANGER).json()["graphs"] == []

    assert client.patch("/api/graphs/acme", json={"name": "ACME!"}, headers=OWNER).json()["name"] == "ACME!"
    assert client.get("/api/graphs/acme", headers=STRANGER).status_code == 403
    assert client.get("/api/graphs/nope", headers=OWNER).status_code == 404

    assert client.post("/api/graphs", json={"slug": "acme", "name": "Dup"}, headers=STRANGER).status_code == 409
    assert client.post("/api/graphs", json={"slug": "Bad Slug", "name": "x"}, headers=OWNER).status_code == 400


def test_graph_delete_owner_only(client, graph):
    assert client.delete("/api/graphs/acme", headers=EDITOR).status_code == 403
    assert client.delete("/api/graphs/acme", headers=OWNER).status_code == 204
    assert client.get("/api/graphs/acme", headers=OWNER).status_code == 404


# --- nodes ------------------------------------------------------------------------

def test_node_lifecycle(client, graph):
    create_node(client, {"kind": "vision", "slug": "vision", "content": "# Vision\n\nWin."})
    create_node(client, {"kind": "icp", "slug": "founders"})
    create_node(client, {"kind": "job", "slug": "ship-fast", "icps": ["icp.founders"]})
    create_node(client, {"kind": "outcome", "slug": "activation", "icps": ["icp.founders"], "jobs": ["job.ship-fast"]})
    create_node(client, {"kind": "opportunity", "slug": "onboarding", "under": "outcome.activation"})
    create_node(client, {"kind": "solution", "slug": "wizard", "under": "opportunity.onboarding"})

    node = client.get("/api/graphs/acme/nodes/solution.wizard", headers=VIEWER).json()["node"]
    assert node["parent"] == "opportunity.onboarding"

    trace = client.get("/api/graphs/acme/nodes/wizard/trace", headers=OWNER).json()
    assert [n["ref"] for n in trace["trace"]] == ["outcome.activation", "opportunity.onboarding", "solution.wizard"]

    context = client.get("/api/graphs/acme/nodes/wizard/context", headers=OWNER).json()
    assert "# Context: solution.wizard" in context["markdown"]
    assert [icp["ref"] for icp in context["icps"]] == ["icp.founders"]
    assert [job["ref"] for job in context["jobs"]] == ["job.ship-fast"]
    assert "## Job Content" in context["markdown"]

    tree = client.get("/api/graphs/acme/tree", headers=OWNER).json()
    outcome = next(r for r in tree["roots"] if r["ref"] == "outcome.activation")
    assert outcome["children"][0]["children"][0]["ref"] == "solution.wizard"

    listing = client.get("/api/graphs/acme/nodes", params={"kind": "icp"}, headers=OWNER).json()["nodes"]
    assert [n["ref"] for n in listing] == ["icp.founders"]


def test_placement_and_slug_rules_enforced(client, graph):
    create_node(client, {"kind": "outcome", "slug": "o"})
    response = client.post("/api/graphs/acme/nodes", json={"kind": "solution", "slug": "s", "under": "outcome.o"}, headers=OWNER)
    assert response.status_code == 400
    assert "not allowed under outcome.o" in response.json()["detail"]

    assert create_node(client, {"kind": "outcome", "slug": "o"}, expect=400)["detail"].endswith("already exists in this graph")
    assert "invalid slug" in create_node(client, {"kind": "outcome", "slug": "Bad"}, expect=400)["detail"]


def test_strategy_date_rules_enforced(client, graph):
    response = client.post("/api/graphs/acme/nodes", json={"kind": "strategy", "slug": "s1"}, headers=OWNER)
    assert response.status_code == 400
    assert "starts and ends" in response.json()["detail"]

    create_node(client, {"kind": "strategy", "slug": "s1", "starts": "2026-01-01", "ends": "2026-06-30"})
    response = client.post(
        "/api/graphs/acme/nodes",
        json={"kind": "strategy", "slug": "s2", "starts": "2026-06-01", "ends": "2026-12-31"},
        headers=OWNER,
    )
    assert response.status_code == 400 and "overlaps" in response.json()["detail"]


def test_version_conflict_on_stale_save(client, graph):
    create_node(client, {"kind": "outcome", "slug": "o"})
    assert client.patch("/api/graphs/acme/nodes/outcome.o", json={"version": 1, "content": "second session"}, headers=EDITOR).status_code == 200
    response = client.patch("/api/graphs/acme/nodes/outcome.o", json={"version": 1, "content": "first session"}, headers=OWNER)
    assert response.status_code == 409
    assert "reload and retry" in response.json()["detail"]
    node = client.get("/api/graphs/acme/nodes/outcome.o", headers=OWNER).json()["node"]
    assert node["content"] == "second session" and node["version"] == 2


def test_delete_cascade_protection(client, graph):
    create_node(client, {"kind": "outcome", "slug": "o"})
    create_node(client, {"kind": "opportunity", "slug": "p", "under": "outcome.o"})
    response = client.delete("/api/graphs/acme/nodes/outcome.o", headers=OWNER)
    assert response.status_code == 409 and "cascade" in response.json()["detail"]
    response = client.delete("/api/graphs/acme/nodes/outcome.o", params={"cascade": "true"}, headers=OWNER)
    assert response.status_code == 200
    assert set(response.json()["deleted"]) == {"opportunity.p", "outcome.o"}


def test_validate_endpoint(client, graph):
    assert client.get("/api/graphs/acme/validate", headers=VIEWER).json() == {"valid": True, "issues": []}


def test_validate_warnings_do_not_break_validity(client, graph):
    create_node(client, {"kind": "outcome", "slug": "o"})
    create_node(client, {"kind": "opportunity", "slug": "floating", "under": "outcome.o"})
    create_node(client, {"kind": "job", "slug": "lonely"})
    payload = client.get("/api/graphs/acme/validate", headers=VIEWER).json()
    assert payload["valid"] is True
    messages = {issue["ref"]: issue for issue in payload["issues"]}
    assert messages["opportunity.floating"]["severity"] == "warning"
    assert messages["job.lonely"]["severity"] == "warning"


def test_job_refs_via_api(client, graph):
    create_node(client, {"kind": "job", "slug": "ship-fast"})
    create_node(client, {"kind": "outcome", "slug": "o"})

    # jobs are set and cleared via PATCH
    node = client.get("/api/graphs/acme/nodes/outcome.o", headers=OWNER).json()["node"]
    patched = client.patch(
        "/api/graphs/acme/nodes/outcome.o",
        json={"version": node["version"], "jobs": ["job.ship-fast"]},
        headers=EDITOR,
    )
    assert patched.status_code == 200 and patched.json()["node"]["jobs"] == ["job.ship-fast"]

    # only outcomes and opportunities may reference jobs
    response = client.post(
        "/api/graphs/acme/nodes",
        json={"kind": "icp", "slug": "devs", "jobs": ["job.ship-fast"]},
        headers=OWNER,
    )
    assert response.status_code == 400 and "cannot reference jobs" in response.json()["detail"]

    # a referenced job cannot be deleted
    response = client.delete("/api/graphs/acme/nodes/job.ship-fast", headers=OWNER)
    assert response.status_code == 409 and "referenced by" in response.json()["detail"]

    # overview exposes job edges and servedBy
    overview = client.get("/api/graphs/acme/overview", headers=OWNER).json()
    assert {"source": "outcome.o", "target": "job.ship-fast", "type": "job"} in overview["edges"]
    job_node = next(n for n in overview["nodes"] if n["ref"] == "job.ship-fast")
    assert job_node["servedBy"] == ["outcome.o"]


# --- roles ---------------------------------------------------------------------------

def test_viewer_cannot_mutate(client, graph):
    response = client.post("/api/graphs/acme/nodes", json={"kind": "outcome", "slug": "o"}, headers=VIEWER)
    assert response.status_code == 403
    assert "editor" in response.json()["detail"]


def test_only_owner_manages_members_and_share_links(client, graph):
    assert client.get("/api/graphs/acme/share-links", headers=EDITOR).status_code == 403
    assert client.put("/api/graphs/acme/members/viewer@simulated.local", json={"role": "editor"}, headers=EDITOR).status_code == 403
    members = client.get("/api/graphs/acme/members", headers=VIEWER).json()["members"]
    assert {m["role"] for m in members} == {"owner", "editor", "viewer"}


def test_graph_keeps_at_least_one_owner(client, graph):
    response = client.delete("/api/graphs/acme/members/owner@simulated.local", headers=OWNER)
    assert response.status_code == 409
    response = client.put("/api/graphs/acme/members/owner@simulated.local", json={"role": "viewer"}, headers=OWNER)
    assert response.status_code == 409


# --- share links -------------------------------------------------------------------------

def test_share_link_grants_readonly_access(client, graph):
    create_node(client, {"kind": "outcome", "slug": "o"})
    token = client.post("/api/graphs/acme/share-links", headers=OWNER).json()["token"]

    headers = {"X-Share-Token": token}
    overview = client.get("/api/graphs/acme/overview", headers=headers).json()
    assert overview["readOnly"] is True
    assert [n["ref"] for n in overview["nodes"]] == ["outcome.o"]
    assert client.get("/api/graphs/acme/nodes/outcome.o", params={"share": token}).status_code == 200

    # share token is graph-scoped and read-only
    assert client.post("/api/graphs/acme/nodes", json={"kind": "outcome", "slug": "x"}, headers=headers).status_code == 403
    other = client.post("/api/graphs", json={"slug": "other", "name": "Other"}, headers=STRANGER)
    assert other.status_code == 201
    assert client.get("/api/graphs/other/overview", headers=headers).status_code == 401

    # public token resolver used by the share UI
    resolved = client.get(f"/api/share/{token}")
    assert resolved.status_code == 200 and resolved.json()["graph"]["slug"] == "acme"
    assert client.get("/api/share/not-a-token").status_code == 404

    # revocation kills it
    link_id = client.get("/api/graphs/acme/share-links", headers=OWNER).json()["shareLinks"][0]["id"]
    assert client.delete(f"/api/graphs/acme/share-links/{link_id}", headers=OWNER).status_code == 204
    assert client.get("/api/graphs/acme/overview", headers=headers).status_code == 401


# --- flywheel ---------------------------------------------------------------------------

def test_flywheel_crud(client, graph):
    assert client.get("/api/graphs/acme/flywheel", headers=OWNER).json()["flywheel"] is None
    client.put("/api/graphs/acme/flywheel", json={"slug": "loop", "title": "Loop", "content": "The loop."}, headers=EDITOR)
    client.post("/api/graphs/acme/flywheel/nodes", json={"slug": "ship", "content": "Shipping attracts users."}, headers=EDITOR)
    client.post("/api/graphs/acme/flywheel/nodes", json={"slug": "learn", "content": "Learning improves shipping.", "next": ["ship"]}, headers=EDITOR)
    response = client.patch("/api/graphs/acme/flywheel/nodes/ship", json={"next": ["flywheel-node.learn"], "status": "active"}, headers=EDITOR)
    flywheel = response.json()["flywheel"]
    ship = next(n for n in flywheel["nodes"] if n["slug"] == "ship")
    assert ship["next"] == ["flywheel-node.learn"] and ship["status"] == "active"

    assert client.put("/api/graphs/acme/flywheel", json={"slug": "loop"}, headers=VIEWER).status_code == 403

    overview = client.get("/api/graphs/acme/overview", headers=OWNER).json()
    assert overview["flywheel"]["slug"] == "loop"

    assert client.delete("/api/graphs/acme/flywheel/nodes/learn", headers=EDITOR).status_code == 204
    assert client.delete("/api/graphs/acme/flywheel", headers=EDITOR).status_code == 204
    assert client.get("/api/graphs/acme/flywheel", headers=OWNER).json()["flywheel"] is None


def test_selector_ambiguity_is_409(client, graph):
    create_node(client, {"kind": "outcome", "slug": "same"})
    create_node(client, {"kind": "icp", "slug": "same"})
    response = client.get("/api/graphs/acme/nodes/same", headers=OWNER)
    assert response.status_code == 409 and "ambiguous" in response.json()["detail"]
