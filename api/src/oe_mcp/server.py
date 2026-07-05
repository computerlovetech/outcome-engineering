"""Read-only MCP server: thin proxy over the HTTP API.

Auth: the caller's bearer token (Authorization header on the MCP HTTP
transport) is forwarded to the API, which validates it (OIDC or simulation
mode). For dev/stdio use, OE_MCP_TOKEN supplies a fallback token.
"""

from __future__ import annotations

import os

import httpx
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers

mcp = FastMCP(
    "outcome-engineering",
    instructions=(
        "Read-only access to Outcome Graphs: list graphs, "
        "inspect trees and nodes, fetch agent context, and validate graphs."
    ),
)


def _api_url() -> str:
    return os.environ.get("OE_MCP_API_URL", "http://localhost:8000").rstrip("/")


def _token() -> str:
    try:
        header = get_http_headers().get("authorization", "")
    except Exception:
        header = ""
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    token = os.environ.get("OE_MCP_TOKEN")
    if token:
        return token
    raise ValueError("no bearer token: send an Authorization header or set OE_MCP_TOKEN")


def _get(path: str, params: dict | None = None) -> dict:
    response = httpx.get(
        _api_url() + path,
        params=params,
        headers={"Authorization": f"Bearer {_token()}"},
        timeout=30,
    )
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise ValueError(f"API error {response.status_code}: {detail}")
    return response.json()


@mcp.tool
def list_graphs() -> dict:
    """List the Outcome Graphs the authenticated user is a member of."""
    return _get("/api/graphs")


@mcp.tool
def get_tree(graph: str) -> dict:
    """Get the full node tree of a graph (by slug or id)."""
    return _get(f"/api/graphs/{graph}/tree")


@mcp.tool
def list_nodes(graph: str, kind: str | None = None) -> dict:
    """List nodes in a graph, optionally filtered by kind (vision, strategy,
    icp, job, outcome, opportunity, solution, assumption-test, prd)."""
    return _get(f"/api/graphs/{graph}/nodes", params={"kind": kind} if kind else None)


@mcp.tool
def show_node(graph: str, selector: str) -> dict:
    """Get one node's full content and relations. Selector: '<kind>.<slug>',
    bare slug (if unique), or node uuid."""
    return _get(f"/api/graphs/{graph}/nodes/{selector}")


@mcp.tool
def get_context(graph: str, selector: str) -> str:
    """Get deterministic agent-facing markdown context for a node: vision,
    current strategy, related ICPs and jobs, ancestor chain, the node,
    children, and flywheel."""
    return _get(f"/api/graphs/{graph}/nodes/{selector}/context")["markdown"]


@mcp.tool
def get_trace(graph: str, selector: str) -> dict:
    """Get a node's ancestor chain (trace) and children."""
    return _get(f"/api/graphs/{graph}/nodes/{selector}/trace")


@mcp.tool
def validate_graph(graph: str) -> dict:
    """Validate a graph against the Outcome Graph rules; returns issues."""
    return _get(f"/api/graphs/{graph}/validate")


@mcp.tool
def get_flywheel(graph: str) -> dict:
    """Get a graph's flywheel (nodes and next-step edges), if it has one."""
    return _get(f"/api/graphs/{graph}/flywheel")


def main() -> None:
    mcp.run(
        transport="http",
        host=os.environ.get("OE_MCP_HOST", "0.0.0.0"),
        port=int(os.environ.get("OE_MCP_PORT", "8001")),
    )


if __name__ == "__main__":
    main()
