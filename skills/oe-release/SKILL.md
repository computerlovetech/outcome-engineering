---
name: oe-release
description: >
  Release process for the outcome-engineering package. Handles version bumping
  (major/minor/patch/beta), changelog updates, pre-release checks, git tagging,
  and monitoring the GitHub Actions publish pipeline. Use this skill whenever
  the user wants to cut a release, bump the version, publish to PyPI, create a
  release tag, or asks about shipping a new Outcome Engineering version.
---

# Outcome Engineering Release Process

Outcome Engineering releases are tag-driven. Pushing a `vX.Y.Z` tag triggers the
GitHub Actions publish pipeline, which runs tests, builds the package, publishes
to PyPI through trusted publishing, and creates a GitHub Release.

Prepare the release so the tag pipeline succeeds on the first try.

## Preconditions

Verify these before editing release files. If any fail, stop and tell the user.

1. Clean working tree: `git status --short`
2. On `main`: `git branch --show-current`
3. Up to date with remote: `git fetch origin` and compare `main` with `origin/main`

If the user has not specified a release type, ask whether this is:

- `patch`: bug fixes or small safe changes
- `minor`: backwards-compatible features
- `major`: breaking changes
- `beta`: pre-release testing build

## Step 1: Inspect Changes

Understand what is being released before touching files.

```sh
git describe --tags --abbrev=0
git log $(git describe --tags --abbrev=0)..HEAD --oneline
```

If there are no tags yet, inspect the relevant history manually:

```sh
git log --oneline
```

Cross-check the commits with the `[Unreleased]` section in `CHANGELOG.md`.
Add missing user-facing changes under standard categories:

- `Added`
- `Changed`
- `Fixed`
- `Removed`
- `Docs`

## Step 2: Run Local Checks

Run the checks that mirror the release pipeline.

```sh
uv run ruff check .
uv run ty check
uv run pytest
uv build
uv run oe validate product
```

If a check fails, fix it before continuing. Do not tag a release from a failing
local state.

## Step 3: Check Release-Sensitive Docs

Update docs only when the release changes user-facing behavior:

- CLI commands or flags changed
- Product graph structure or validation changed
- Installation or skill behavior changed
- Existing examples no longer match current behavior

For CLI surface changes, update the bundled `oe-cli` skill:

- `src/outcome_engineering/skills/oe-cli/SKILL.md`

## Step 4: Bump Version

The package version lives in `pyproject.toml`:

```toml
[project]
version = "X.Y.Z"
```

Calculate the next version from the chosen release type.

For beta releases:

- `0.1.0` -> `0.1.1b1`
- `0.1.1b1` -> `0.1.1b2`
- `0.1.1b2` -> `0.1.1` when promoting to stable

## Step 5: Update Changelog

In `CHANGELOG.md`:

1. Replace `## [Unreleased]` with a new empty `## [Unreleased]` section followed by `## [X.Y.Z] - YYYY-MM-DD`.
2. Move release entries under the version heading.
3. Keep entries concise and useful to a user scanning release notes.

The GitHub Release job extracts the matching version section from
`CHANGELOG.md`, so the heading must be exactly:

```md
## [X.Y.Z] - YYYY-MM-DD
```

## Step 6: Commit, Tag, and Push

Stage the release files:

```sh
git add pyproject.toml CHANGELOG.md
git add README.md skills src/outcome_engineering/skills docs tests
git commit -m "release: vX.Y.Z"
git tag vX.Y.Z
```

Before pushing, show the user:

- version being released
- changelog section
- files changed
- tag to push

Wait for explicit user confirmation before pushing:

```sh
git push origin main
git push origin vX.Y.Z
```

## Step 7: Monitor Pipeline

After pushing the tag, monitor the publish workflow:

```sh
gh run list --workflow=publish.yml --limit=1
gh run watch $(gh run list --workflow=publish.yml --limit=1 --json databaseId -q '.[0].databaseId')
```

The pipeline stages are:

1. Quality Checks: `uv run ruff check .`, `uv run ty check`, and `uv run pytest`
2. Build Package: `uv build` and tag/version verification
3. Publish to PyPI: trusted publishing through OIDC
4. Create GitHub Release: release notes from `CHANGELOG.md`

If the pipeline fails, inspect logs:

```sh
gh run view <run-id> --log-failed
```

## Step 8: Verify Release

After the pipeline succeeds:

```sh
pip index versions outcome-engineering
gh release view vX.Y.Z
```

Report the PyPI and GitHub Release links:

- `https://pypi.org/project/outcome-engineering/X.Y.Z/`
- the URL from `gh release view`

## Recovery

If a pushed tag must be retried:

1. Fix the issue.
2. Ask the user before deleting any tag.
3. Delete local and remote tags only after confirmation:

```sh
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z
```

4. Amend the release commit or create a fix commit.
5. Re-tag and push again.

Deleting tags is destructive. Never do it without explicit confirmation.
