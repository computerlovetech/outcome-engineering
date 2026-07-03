# Diary: Rename Product Graph to Outcome Graph

This task renamed the user-facing and documentation terminology from Product Graph to Outcome Graph across the Outcome Engineering project.

## Step 1: Rename the term across the project

**Author:** main

### Prompt Context

**Verbatim prompt:** One thing I would like to change is to instead call it an "Outcome Graph" instead of a "Product Graph". Please fix that throughout the project.
**Interpretation:** Replace the project's visible "Product Graph" terminology with "Outcome Graph" everywhere it appears.
**Inferred intent:** Align the project language with the preferred branded concept name while preserving existing graph behavior and code structure.

### What I did

I created a dedicated worktree at `.worktrees/rename-product-graph` on branch `rename-product-graph` before editing. I replaced the term in root docs, changelog entries, package metadata, CLI help text, MCP tool descriptions, core docstrings, bundled agent skills, and frontend copy. The touched files were `/AGENTS.md`, `/README.md`, `/CHANGELOG.md`, `/api/pyproject.toml`, `/api/src/oe_cli/main.py`, `/api/src/oe_cli/skills/oe-best-practices/SKILL.md`, `/api/src/oe_cli/skills/oe-cli/SKILL.md`, `/api/src/oe_cli/skills/oe-graph-audit/SKILL.md`, `/api/src/oe_cli/skills/oe-grill/SKILL.md`, `/api/src/oe_cli/skills/oe-validate/SKILL.md`, `/api/src/oe_core/__init__.py`, `/api/src/oe_core/model.py`, `/api/src/oe_mcp/server.py`, `/frontend/src/lib/GraphView.svelte`, `/frontend/src/routes/+page.svelte`, and `/skills/oe-release/SKILL.md`.

### Why

The old term appeared in the public README, UI labels, CLI and MCP descriptions, and packaged skill metadata. Updating only one surface would leave inconsistent language for users and agents.

### What worked

`rg -n -i "product graph|product-graph|product_graph|ProductGraph|productGraph"` was useful for finding the relevant spelling variants. `uv run pytest` passed with 72 tests after the rename. The frontend production build passed when run with `PUBLIC_API_BASE_URL=http://localhost:8000`.

### What didn't work

The first frontend build attempt failed because this new worktree had no frontend dependencies installed:

```sh
npm run build
```

The error was:

```text
sh: vite: command not found
```

After `npm install`, the next build reached Vite but failed because SvelteKit's static public env import requires the documented API URL to be defined:

```sh
npm run build
```

The error was:

```text
src/lib/api.ts (7:9): "PUBLIC_API_BASE_URL" is not exported by "\0virtual:env/static/public", imported by "src/lib/api.ts".
```

Rerunning with `PUBLIC_API_BASE_URL=http://localhost:8000 npm run build` passed.

### What I learned

The term is part of user-facing language rather than a storage or API identifier. The underlying route and data model still use generic graph naming, so this change did not require schema, API contract, or filesystem convention changes.

### What was tricky

The mechanical replacement created awkward grammar in a few places, such as an incorrect article before "Outcome Graph" and duplicated phrases. Those needed a manual cleanup pass.

### What warrants review

Review the CLI, MCP, bundled skill descriptions, and frontend copy to decide whether "Outcome Graph" should always be title-cased or whether sentence-case "outcome graph" is preferred in prose.

### Future work

If the hosted local stack should reflect this branch immediately, rebuild and restart Docker Compose from the worktree so the currently running containers pick up the renamed UI and help text.
