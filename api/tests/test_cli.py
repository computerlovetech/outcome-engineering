"""CLI tests: Typer runner with HTTP routed into an in-process test app."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from oe_api.app import create_app
from oe_api.settings import Settings
from oe_cli import client as cli_client
from oe_cli.main import app as cli_app
from oe_store.models import Base

runner = CliRunner()


@pytest.fixture
def cli(monkeypatch, tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    settings = Settings(auth_mode="simulation", run_migrations_on_startup=False, database_url="sqlite://")
    app = create_app(settings)
    app.state.session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    test_client = TestClient(app)

    def fake_request(method, url, **kwargs):
        path = url.replace("http://testserver", "")
        kwargs.pop("timeout", None)
        return test_client.request(method, path, **kwargs)

    monkeypatch.setattr(cli_client.httpx, "request", fake_request)
    monkeypatch.setenv("OE_API_URL", "http://testserver")
    monkeypatch.setenv("OE_TOKEN", "dev")
    monkeypatch.setenv("OE_CONFIG_DIR", str(tmp_path / "config"))

    # seed a small graph over the API
    headers = {"Authorization": "Bearer dev"}
    assert test_client.post("/api/graphs", json={"slug": "acme", "name": "Acme"}, headers=headers).status_code == 201
    for payload in (
        {"kind": "vision", "slug": "vision", "content": "# Vision\n\nWin."},
        {"kind": "icp", "slug": "founders"},
        {"kind": "outcome", "slug": "activation", "icps": ["icp.founders"]},
        {"kind": "opportunity", "slug": "onboarding", "under": "outcome.activation"},
    ):
        assert test_client.post("/api/graphs/acme/nodes", json=payload, headers=headers).status_code == 201
    return test_client


def invoke(*args):
    return runner.invoke(cli_app, list(args))


def test_graphs(cli):
    result = invoke("graphs")
    assert result.exit_code == 0
    assert "acme" in result.output and "owner" in result.output


def test_tree(cli):
    result = invoke("tree", "-g", "acme")
    assert result.exit_code == 0
    assert "outcome.activation" in result.output
    assert "opportunity.onboarding" in result.output


def test_list_show_trace_context(cli):
    assert "icp.founders" in invoke("list", "-g", "acme", "-k", "icp").output
    assert "Win." in invoke("show", "vision.vision", "-g", "acme").output
    trace = invoke("trace", "opportunity.onboarding", "-g", "acme").output
    assert trace.index("outcome.activation") < trace.index("opportunity.onboarding")
    context = invoke("context", "outcome.activation", "-g", "acme").output
    assert "# Context: outcome.activation" in context


def test_validate(cli):
    result = invoke("validate", "-g", "acme")
    assert result.exit_code == 0 and "OK" in result.output


def test_not_found_is_clean_error(cli):
    result = invoke("show", "outcome.nope", "-g", "acme")
    assert result.exit_code == 1
    assert "404" in result.output


def test_login_token_and_logout(cli, monkeypatch, tmp_path):
    monkeypatch.delenv("OE_TOKEN")
    assert invoke("login", "--token", "dev").exit_code == 0
    result = invoke("whoami")
    assert result.exit_code == 0 and "dev@simulated.local" in result.output
    assert invoke("logout").exit_code == 0
    assert invoke("whoami").exit_code == 1


def test_install_skill_to_target(cli, tmp_path):
    target = tmp_path / "skills" / "oe-cli"
    result = invoke("install-skill", "--target", str(target))
    assert result.exit_code == 0
    assert (target / "SKILL.md").is_file()


def test_install_project_skills(cli, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = invoke("install", "--skills")
    assert result.exit_code == 0
    assert (tmp_path / ".claude" / "skills" / "oe-cli" / "SKILL.md").is_file()
    assert (tmp_path / ".claude" / "skills" / "oe-best-practices" / "SKILL.md").is_file()
