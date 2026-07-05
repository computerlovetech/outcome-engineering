"""Domain errors. The API layer maps these to HTTP status codes."""

from __future__ import annotations


class DomainError(Exception):
    """Base for all domain rule violations."""


class PlacementError(DomainError):
    """Node kind not allowed under the chosen parent."""


class SlugError(DomainError):
    """Invalid or duplicate slug."""


class StrategyDateError(DomainError):
    """Missing/invalid strategy dates or overlapping periods."""


class IcpReferenceError(DomainError):
    """Invalid ICP reference (wrong referrer kind or target not an ICP)."""


class JobReferenceError(DomainError):
    """Invalid job reference (wrong referrer kind or target not a job)."""


class CascadeRequiredError(DomainError):
    """Delete refused because the node has descendants and cascade was not set."""


class NotFoundError(DomainError):
    """Selector did not resolve to a node."""


class AmbiguousSelectorError(DomainError):
    """Bare-slug selector matched more than one node."""


class VersionConflictError(DomainError):
    """Optimistic-concurrency version mismatch."""
