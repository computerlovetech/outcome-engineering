"""The `oe` CLI: read-only commands against the hosted API, browser login,
and the agent-skill installer."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from oe_cli import auth_flow, client, config
from oe_cli.skill_installer import (
    install_project_skills,
    install_skill,
    install_skills_for_agent,
    parse_skills_option,
)

app = typer.Typer(help="Outcome Graph tooling.", no_args_is_help=True)

GRAPH_OPTION = typer.Option(..., "--graph", "-g", envvar="OE_GRAPH", help="Graph slug or id.")


def _json_option():
    return typer.Option(False, "--json", help="Print the raw JSON payload.")


# --- auth ------------------------------------------------------------------------


@app.command()
def login(
    token: str | None = typer.Option(None, "--token", help="Store a plain bearer token (simulation-mode servers)."),
    no_browser: bool = typer.Option(False, "--no-browser", help="Print the verification URL instead of opening a browser."),
) -> None:
    """Log in via the OIDC device flow (or store a simulation token)."""
    try:
        if token is not None:
            auth_flow.store_plain_token(token)
            typer.echo("Token stored.")
            return
        auth_flow.device_login(open_browser=not no_browser, echo=typer.echo)
    except auth_flow.LoginError as error:
        client.die(error)


@app.command()
def logout() -> None:
    """Forget stored credentials."""
    auth_flow.logout()
    typer.echo("Logged out.")


@app.command()
def whoami() -> None:
    """Show the logged-in user as the server sees it."""
    try:
        me = client.get("/api/me")
    except client.ApiError as error:
        client.die(error)
    typer.echo(f"{me['name'] or me['email']} <{me['email']}> ({me['id']})")


# --- reads ------------------------------------------------------------------------


@app.command()
def graphs(as_json: bool = _json_option()) -> None:
    """List graphs you are a member of."""
    try:
        payload = client.get("/api/graphs")
    except client.ApiError as error:
        client.die(error)
    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return
    if not payload["graphs"]:
        typer.echo("No graphs yet.")
        return
    for graph in payload["graphs"]:
        typer.echo(f"{graph['slug']}\t{graph['name']}\t({graph['role']})")


@app.command("tree")
def tree_command(graph: str = GRAPH_OPTION, as_json: bool = _json_option()) -> None:
    """Print the Outcome Graph tree."""
    try:
        payload = client.get(f"/api/graphs/{graph}/tree")
    except client.ApiError as error:
        client.die(error)
    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return
    typer.echo(graph)
    roots = payload["roots"]
    for index, root in enumerate(roots):
        _print_tree_node(root, prefix="", is_last=index == len(roots) - 1)


def _print_tree_node(node: dict, prefix: str, is_last: bool) -> None:
    connector = "└── " if is_last else "├── "
    typer.echo(f"{prefix}{connector}{node['ref']}")
    child_prefix = prefix + ("    " if is_last else "│   ")
    children = node["children"]
    for index, child in enumerate(children):
        _print_tree_node(child, prefix=child_prefix, is_last=index == len(children) - 1)


@app.command("list")
def list_command(
    graph: str = GRAPH_OPTION,
    kind: str | None = typer.Option(None, "--kind", "-k", help="Filter by node kind."),
    as_json: bool = _json_option(),
) -> None:
    """List nodes in a graph."""
    try:
        params = {"kind": kind} if kind else {}
        payload = client.get(f"/api/graphs/{graph}/nodes", params=params)
    except client.ApiError as error:
        client.die(error)
    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return
    for node in payload["nodes"]:
        typer.echo(f"{node['ref']}\t{node['title']}")


@app.command()
def show(selector: str, graph: str = GRAPH_OPTION, as_json: bool = _json_option()) -> None:
    """Show a node's content."""
    try:
        payload = client.get(f"/api/graphs/{graph}/nodes/{selector}")
    except client.ApiError as error:
        client.die(error)
    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return
    typer.echo(payload["node"]["content"])


@app.command()
def trace(selector: str, graph: str = GRAPH_OPTION, as_json: bool = _json_option()) -> None:
    """Print a node's ancestor chain and children."""
    try:
        payload = client.get(f"/api/graphs/{graph}/nodes/{selector}/trace")
    except client.ApiError as error:
        client.die(error)
    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return
    for node in payload["trace"]:
        typer.echo(node["ref"])
    if payload["children"]:
        typer.echo("children:")
        for child in payload["children"]:
            typer.echo(f"  {child['ref']}")


@app.command()
def context(selector: str, graph: str = GRAPH_OPTION, as_json: bool = _json_option()) -> None:
    """Print agent-facing markdown context for a node."""
    try:
        payload = client.get(f"/api/graphs/{graph}/nodes/{selector}/context")
    except client.ApiError as error:
        client.die(error)
    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return
    typer.echo(payload["markdown"])


@app.command()
def validate(graph: str = GRAPH_OPTION, as_json: bool = _json_option()) -> None:
    """Validate a graph and list any issues."""
    try:
        payload = client.get(f"/api/graphs/{graph}/validate")
    except client.ApiError as error:
        client.die(error)
    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return
    if payload["valid"]:
        typer.echo(f"OK: {graph} is a valid Outcome Graph")
        return
    typer.echo(f"Invalid Outcome Graph: {graph}")
    for issue in payload["issues"]:
        typer.echo(f"- {issue['ref']}: {issue['message']}")
    raise typer.Exit(code=1)


# --- skills -------------------------------------------------------------------------


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def install(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", help="Replace the target skill directory if it already exists."),
) -> None:
    """Install bundled assets, including the Outcome Engineering skills."""
    try:
        skill_value = parse_skills_option(ctx.args)
        installed_paths = install_project_skills(skill_value, force=force)
    except (ValueError, FileExistsError) as error:
        client.die(error)
    for installed_at in installed_paths:
        typer.echo(f"Installed skill at {installed_at}")


@app.command("install-skill")
def install_skill_command(
    agent: str = typer.Option("codex", "--agent", "-a", help="Agent tool target: codex, claude, or all."),
    target: Path | None = typer.Option(None, "--target", "-t", help="Exact skill install directory. Overrides --agent."),
    force: bool = typer.Option(False, "--force", help="Replace the target skill directory if it already exists."),
) -> None:
    """Install the bundled Outcome Engineering agent skill."""
    try:
        installed_paths = (
            [install_skill(target=target, force=force)]
            if target is not None
            else install_skills_for_agent(agent, force=force)
        )
    except (FileExistsError, ValueError) as error:
        client.die(error)
    for installed_at in installed_paths:
        typer.echo(f"Installed skill at {installed_at}")


@app.command("config")
def config_command(
    api_url: str | None = typer.Option(None, "--api-url", help="Persist the API base URL."),
) -> None:
    """Show or update CLI configuration."""
    if api_url is not None:
        saved = config.load_config()
        saved["api_url"] = api_url
        config.save_config(saved)
    saved = config.load_config()
    typer.echo(f"api_url: {config.api_url()}")
    typer.echo(f"logged in: {'yes' if saved.get('access_token') else 'no'}")


if __name__ == "__main__":
    app()
