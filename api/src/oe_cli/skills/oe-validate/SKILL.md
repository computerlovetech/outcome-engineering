---
name: oe-validate
description: Use when asked to validate an Outcome Engineering product graph, explain validation errors, or fix graph structure so `oe validate` passes.
---

# OE Validate

Run deterministic commands first; only reason after seeing real output.

## Workflow

1. Validate the graph on the server (see `oe-cli` for login/config):

```sh
oe validate -g <graph>
```

2. If validation passes, report that the graph is structurally valid.

3. If validation fails:
- quote the failing command and each reported issue (node ref + message)
- inspect the affected nodes with `oe show <ref> -g <graph>`
- propose the smallest fix (edits happen in the web UI in v1)
- ask for approval before changing anything

4. After the fix is applied, rerun:

```sh
oe validate -g <graph>
```

Stop when validation passes or when a required product decision is missing.
