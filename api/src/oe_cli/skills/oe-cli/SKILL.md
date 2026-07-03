---
name: oe-cli
description: Use this skill whenever a project uses Outcome Engineering product graphs, the `oe` CLI, the `outcome-engineering` Python package, or the user needs graph structure inspected, traced, validated, or contextualized against an Outcome Engineering server. This skill is the CLI and graph-structure operating manual; use `oe-best-practices` for product content quality, `oe-graph-audit` for method audits, and `oe-grill` for product conversations.
---

# Outcome Engineering

Use the `oe` CLI to read product graphs hosted on an Outcome Engineering
server. The Python package is `outcome-engineering`. The command is `oe`.

Graphs live in a server database (not in the repo). A graph is a tree of
nodes plus an ICP collection and an optional flywheel:

- Kinds: `vision`, `strategy`, `icp`, `outcome`, `opportunity`, `solution`,
  `assumption-test`, `prd`.
- Placement rules: the graph root holds vision (max one), strategies, ICPs,
  and outcomes; outcome → opportunity; opportunity → opportunity | solution;
  solution → assumption-test | prd. Nothing else nests.
- Strategies declare `starts`/`ends` dates; periods must not overlap and
  status is derived from the dates.
- ICPs (ideal customer profiles) are the "who". They are not part of the
  outcome → opportunity → solution trace chain; outcomes and opportunities
  reference them many-to-many, and `oe context` surfaces a node's own plus
  inherited ICPs.
- Assumption tests are the unified concept for the assumptions a solution
  depends on and the work to test them. They live under solutions only.
- Node ids ("refs") are `<kind>.<slug>`. Selectors accept a ref, a bare slug
  (if unique), or the node uuid.

## Setup

```sh
oe config --api-url https://<server>     # persist the API base URL
oe login                                 # OIDC device flow (browser)
oe login --token dev                     # simulation-mode dev servers
oe whoami
```

`OE_API_URL`, `OE_TOKEN`, and `OE_GRAPH` env vars override stored config.

## Default Workflow

Find the graph, inspect it before making product or delivery changes:

```sh
oe graphs
oe tree -g <graph>
oe list -g <graph> --kind outcome
```

Before working on a specific product artifact, trace it and pull context:

```sh
oe trace <selector> -g <graph>
oe context <selector> -g <graph>
```

Use `oe context` before writing a PRD, editing a solution, or implementing
code from a PRD: it prints deterministic markdown covering the trace, related
ICPs, children, vision, current strategy, flywheel, ancestor content, and the
node content.

After graph changes (made via the web UI), validate:

```sh
oe validate -g <graph>
```

## CLI Commands

Keep this section in sync with `oe --help` and `api/src/oe_cli/main.py`.

- `oe login [--token X] [--no-browser]` / `oe logout` / `oe whoami`
- `oe config [--api-url URL]` shows or updates CLI configuration.
- `oe graphs` lists graphs you are a member of.
- `oe tree -g <graph>` prints the graph tree.
- `oe list -g <graph> [--kind KIND]` lists nodes.
- `oe show <selector> -g <graph>` prints a node's markdown content.
- `oe trace <selector> -g <graph>` shows the ancestor chain and children.
- `oe context <selector> -g <graph>` prints deterministic agent context.
- `oe validate -g <graph>` validates the graph; exits 1 with issues listed.
- `oe install --skills` / `--skills=agents` installs the bundled agent skills
  into the project's `.claude/skills` or `.agents/skills`.
- `oe install-skill --agent codex|claude|all [--target DIR] [--force]`
  installs skills into global agent config dirs.

All read commands accept `--json` for the raw payload.

The CLI is read-only in v1: create, edit, and delete happen in the web UI
(which enforces placement rules, slug uniqueness, strategy dates, cascade
deletes, and optimistic concurrency).

## Important Boundary

`oe` manages deterministic structure. It does not make product judgment.

Do not pretend that `oe validate` means the product thinking is good. It only
means the graph structure is valid. Human judgment and user discovery remain
required.

For product content judgment, use `oe-best-practices`. For a graph-wide
quality audit, use `oe-graph-audit`. For conversational product discovery,
use `oe-grill`. For fixing validation failures, use `oe-validate`.
