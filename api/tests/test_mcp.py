"""MCP tests: in-memory FastMCP client, API HTTP routed into a test app."""

from __future__ import annotations

import json

import pytest
from fastmcp import Client
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from oe_api.app import create_app
from oe_api.settings import Settings
from oe_mcp import server as mcp_server
from oe_store.models import Base


@pytest.fixture
def mcp(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    settings = Settings(auth_mode="simulation", run_migrations_on_startup=False, database_url="sqlite://")
    app = create_app(settings)
    app.state.session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    test_client = TestClient(app)

    def fake_get(url, params=None, headers=None, timeout=None):
        return test_client.get(url.replace("http://localhost:8000", ""), params=params, headers=headers)

    monkeypatch.setattr(mcp_server.httpx, "get", fake_get)
    monkeypatch.setenv("OE_MCP_TOKEN", "dev")

    headers = {"Authorization": "Bearer dev"}
    assert test_client.post("/api/graphs", json={"slug": "acme", "name": "Acme"}, headers=headers).status_code == 201
    for payload in (
        {"kind": "outcome", "slug": "activation"},
        {"kind": "opportunity", "slug": "onboarding", "under": "outcome.activation"},
    ):
        assert test_client.post("/api/graphs/acme/nodes", json=payload, headers=headers).status_code == 201
    return mcp_server.mcp


async def call(mcp, tool, **kwargs):
    async with Client(mcp) as client:
        result = await client.call_tool(tool, kwargs)
        return result.data if result.data is not None else json.loads(result.content[0].text)


async def test_list_graphs(mcp):
    payload = await call(mcp, "list_graphs")
    assert [g["slug"] for g in payload["graphs"]] == ["acme"]


async def test_tree_and_nodes(mcp):
    tree = await call(mcp, "get_tree", graph="acme")
    assert tree["roots"][0]["ref"] == "outcome.activation"
    nodes = await call(mcp, "list_nodes", graph="acme", kind="opportunity")
    assert [n["ref"] for n in nodes["nodes"]] == ["opportunity.onboarding"]


async def test_show_context_trace_validate(mcp):
    node = await call(mcp, "show_node", graph="acme", selector="onboarding")
    assert node["node"]["parent"] == "outcome.activation"
    context = await call(mcp, "get_context", graph="acme", selector="outcome.activation")
    assert "# Context: outcome.activation" in context
    trace = await call(mcp, "get_trace", graph="acme", selector="opportunity.onboarding")
    assert [n["ref"] for n in trace["trace"]] == ["outcome.activation", "opportunity.onboarding"]
    validation = await call(mcp, "validate_graph", graph="acme")
    assert validation["valid"] is True


async def test_api_error_surfaces(mcp):
    with pytest.raises(Exception, match="404"):
        await call(mcp, "show_node", graph="acme", selector="outcome.nope")
