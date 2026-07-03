# Outcome Engineering

Outcome Engineering turns messy product thinking into a **product graph** that
humans and agents can challenge, trace, and update: vision, strategy, ideal
customer profiles (ICPs), outcomes, opportunities, solutions, assumption
tests, PRDs — plus a flywheel describing the causal loop that compounds.

It is a multi-tenant web application:

- **Postgres** stores the graphs.
- **One FastAPI service** (`api/`) is the single read/write path. It enforces
  the model at mutation time: placement rules, slug uniqueness, strategy date
  rules, cascade-delete protection, optimistic concurrency (version + 409).
- **SvelteKit frontend** (`frontend/`) — an Excalidraw-style canvas: strategic
  overview (vision / strategy / ICPs / outcomes), focus into an outcome's
  trace subtree, side-panel markdown editing, model-constrained child
  creation, flywheel view, graph sharing.
- **MCP server** (read-only) so agents can list graphs, read trees and nodes,
  fetch context, and validate.
- **`oe` CLI** (read-only) with browser login and the agent-skill installer.
- **Generic OIDC auth**: oauth2-proxy in front of the frontend, JWT (JWKS)
  validation in the API. Auth0 is just the documented example provider.

## Quick start (local, no auth provider)

Requires Docker.

```sh
docker compose up --build
open http://localhost:3000
```

The stack runs in **simulation auth**: sign in with any token (e.g. `dev`) —
each distinct token is its own dev user. Create a graph, add a vision,
strategy, ICPs and outcomes, drill into opportunities → solutions →
assumption tests / PRDs, add a flywheel, and share a public read-only link
from the graph's settings page (works in an incognito window).

Services:

| Service  | URL                     |
| -------- | ----------------------- |
| frontend | http://localhost:3000   |
| api      | http://localhost:8000   |
| mcp      | http://localhost:8001/mcp |

## Development

Backend (Python 3.11+, [uv](https://docs.astral.sh/uv/)):

```sh
cd api
uv sync
uv run pytest                       # domain + store + API + CLI + MCP tests
OE_DATABASE_URL=sqlite:///dev.db uv run uvicorn --factory oe_api.app:main
```

Frontend (Node 22+):

```sh
cd frontend
npm install
cp .env.example .env                # PUBLIC_API_BASE_URL
npm run dev
```

The API defaults to `OE_AUTH_MODE=simulation`, so any bearer token works
locally. Alembic migrations run automatically on API startup.

### Repo layout

    api/src/oe_core/    pure domain: kinds, placement rules, validation,
                        selector resolution, context assembly
    api/src/oe_store/   SQLAlchemy models, Alembic migrations, GraphStore
    api/src/oe_api/     FastAPI app: routes, auth, authz, settings
    api/src/oe_mcp/     FastMCP read-only tools (proxies the API)
    api/src/oe_cli/     Typer CLI (`oe`) + bundled agent skills
    frontend/           SvelteKit (adapter-node) UI

## CLI

```sh
uv tool install outcome-engineering        # or: uv run oe ... from api/
oe config --api-url https://oe.example.com
oe login                                   # OIDC device flow (browser)
oe login --token dev                       # simulation-mode servers
oe graphs
oe tree -g my-graph
oe list -g my-graph --kind outcome
oe show outcome.activation -g my-graph
oe trace solution.wizard -g my-graph
oe context solution.wizard -g my-graph     # agent-facing markdown context
oe validate -g my-graph
oe install --skills                        # install agent skills into ./.claude/skills
oe install-skill --agent all               # install into ~/.claude + ~/.codex
```

Selectors are `<kind>.<slug>`, a bare slug (if unique), or a node uuid.
`OE_API_URL`, `OE_TOKEN`, and `OE_GRAPH` env vars override the stored config
(`~/.config/oe/`).

## MCP

The `mcp` service exposes read-only tools (`list_graphs`, `get_tree`,
`list_nodes`, `show_node`, `get_context`, `get_trace`, `validate_graph`,
`get_flywheel`) over streamable HTTP. Add it to Claude Code:

```sh
claude mcp add --transport http outcome-engineering http://localhost:8001/mcp \
  --header "Authorization: Bearer dev"
```

The bearer token is forwarded to the API and validated there (simulation or
OIDC, same as any client).

## Deploying with Coolify

The compose file has no reverse proxy and no TLS — Coolify provides both.

1. Create a Docker Compose resource pointing at this repository.
2. Set env vars: `POSTGRES_PASSWORD`, `PUBLIC_API_BASE_URL` (the public URL
   of the API, e.g. `https://oe-api.example.com`), `OE_CORS_ORIGINS` (the
   frontend's public URL), and the OIDC vars below.
3. Expose `frontend` (3000) and `api` (8000) through Coolify domains. Expose
   `mcp` (8001) if agents should reach it.
4. To require login in front of the web UI, enable the auth profile
   (`COMPOSE_PROFILES=auth`) and route the frontend domain at `oauth2-proxy`
   (4180) instead of `frontend`.

## OIDC setup (Auth0 walkthrough)

No Auth0-specific code exists — any OIDC provider works (Keycloak, Google,
GitHub via an OIDC bridge, Entra ID, ...). Auth0 as the worked example:

1. **API**: In Auth0, create an API (identifier = your audience, e.g.
   `https://oe-api.example.com`). Configure the api service:

   ```
   OE_AUTH_MODE=oidc
   OE_OIDC_ISSUER=https://YOUR_TENANT.auth0.com/
   OE_OIDC_JWKS_URL=https://YOUR_TENANT.auth0.com/.well-known/jwks.json
   OE_OIDC_AUDIENCE=https://oe-api.example.com
   ```

   Users are upserted on first authenticated request from the JWT claims
   (`sub`, `email`, `name`).

2. **Web UI**: Create a Regular Web Application in Auth0 (callback
   `https://YOUR_APP_DOMAIN/oauth2/callback`). Configure oauth2-proxy:

   ```
   COMPOSE_PROFILES=auth
   OAUTH2_PROXY_CLIENT_ID=...
   OAUTH2_PROXY_CLIENT_SECRET=...
   OAUTH2_PROXY_COOKIE_SECRET=$(openssl rand -base64 32 | head -c 32)
   OAUTH2_PROXY_REDIRECT_URL=https://YOUR_APP_DOMAIN/oauth2/callback
   ```

   oauth2-proxy forwards the user's access token to the frontend, which uses
   it as the API bearer.

3. **CLI**: Create a Native application in Auth0 with the Device Code grant
   enabled. Then:

   ```sh
   OE_OIDC_ISSUER=https://YOUR_TENANT.auth0.com \
   OE_OIDC_CLIENT_ID=... \
   OE_OIDC_AUDIENCE=https://oe-api.example.com \
   oe login
   ```

   Tokens (incl. refresh token) are stored in `~/.config/oe/` and refreshed
   automatically.

For Keycloak/Google, substitute the issuer/JWKS/client values; the flow is
identical because everything speaks plain OIDC.

## Roles and sharing

Each graph has members with a role: **owner** (manage members, share links,
rename/delete the graph), **editor** (create/edit/delete nodes and the
flywheel), **viewer** (read-only). Owners can mint **public share links** —
unguessable URLs that grant read-only access to that one graph without login;
revoke them any time from graph settings.

## API sketch

All under `/api`, JSON, `Authorization: Bearer <token>` (or
`X-Share-Token`/`?share=` for share links). Highlights:

- `GET/POST /graphs`, `GET/PATCH/DELETE /graphs/{g}`
- `GET /graphs/{g}/overview|tree|validate`
- `GET/POST /graphs/{g}/nodes`, `GET/PATCH/DELETE /graphs/{g}/nodes/{selector}`
  (PATCH requires `version`; a stale version returns 409)
- `GET /graphs/{g}/nodes/{selector}/trace|context`
- `GET /graphs/{g}/members`, `PUT/DELETE /graphs/{g}/members/{user}` (owner)
- `GET/POST /graphs/{g}/share-links`, `DELETE .../share-links/{id}` (owner)
- `GET/PUT/DELETE /graphs/{g}/flywheel`, CRUD under `/flywheel/nodes`
- `GET /share/{token}` — public share-token resolver

Interactive docs at `/docs` on the API service.
