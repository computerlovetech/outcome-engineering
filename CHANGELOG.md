# Changelog

All notable changes to this project are documented in this file.

The format follows Keep a Changelog, and this project uses semantic versioning.

## [Unreleased]

## [0.1.3] - 2026-07-03

### Added

- Released the open-source multi-tenant Outcome Engineering web app, including
  the FastAPI API, Postgres store, SvelteKit frontend, read-only MCP server,
  HTTP CLI, Docker Compose deployment, OIDC auth support, and bundled agent
  skills.

### Fixed

- Fixed GitHub Actions release/test workflows for the new `api/` package
  layout.

## [0.1.2] - 2026-07-01

### Added

- Added a hosted read-only graph HTTP API for serving Outcome Graphs.
- Added a full Outcome Graph overview to the graph UI.
- Added an experimental strategy flywheel graph view.
- Added ICP guidance to the `oe-best-practices` skill.

### Changed

- Decoupled bundled skills so `oe-cli` owns CLI usage, `oe-best-practices` owns product content guidance, `oe-graph-audit` applies best practices to graph audits, `oe-grill` focuses on product questioning, and `oe-validate` wraps validation repair.
- Moved shipped skill source to `src/outcome_engineering/skills` only and updated agr dogfooding to install those canonical skill paths.

### Removed

- Removed `oe-release` from bundled package skills; it remains a repo-local maintenance skill.

## [0.1.1] - 2026-06-29

### Added

- Added GitHub Actions checks for tests, Ruff linting, ty type checking, and package builds.
- Added a tag-driven PyPI publish workflow that builds from `v*` tags, verifies the tag matches `pyproject.toml`, publishes through trusted publishing, and creates a GitHub Release from the changelog.
- Added the `oe-release` bundled skill for preparing, tagging, publishing, monitoring, and recovering Outcome Engineering releases.
- Added `CHANGELOG.md` as the source for GitHub Release notes.

### Fixed

- Fixed ty findings in the graph server request handler and bundled skill installer.

## [0.1.0] - 2026-06-29

### Added

- Initial Outcome Engineering CLI for validating, inspecting, serving, and editing repo-native Outcome Graphs.
