# Outcome Engineering

A multi-tenant web app for Outcome Graphs: vision, strategy, ICPs, outcomes,
opportunities, solutions, assumption tests, PRDs, and a flywheel — stored in
Postgres and served through one FastAPI service with a SvelteKit UI, an `oe`
CLI, and a read-only MCP server.

Layout:

- `api/` — Python package (uv). `oe_core` is the pure domain (placement rules,
  validation, selectors, context assembly); `oe_store` is SQLAlchemy/Alembic;
  `oe_api` the FastAPI service (the single read/write path); `oe_mcp` the MCP
  proxy; `oe_cli` the Typer CLI including the bundled agent skills.
- `frontend/` — SvelteKit (adapter-node) UI.
- `docker-compose.yml` — postgres, api, mcp, frontend (+ oauth2-proxy under
  the `auth` profile).

Run tests from `api/` with `uv run pytest`. Run the frontend checks from
`frontend/` with `npm run check`. `docker compose up --build` gives a full
local stack in simulation auth (sign in with any token).

The `oe-cli` skill in `api/src/oe_cli/skills/oe-cli/SKILL.md` is the
agent-facing manual for the CLI; keep it in sync when the command surface or
graph model changes.
