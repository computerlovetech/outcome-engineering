"""Request bodies."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class GraphCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=255)


class GraphPatch(BaseModel):
    name: str | None = None


class MemberPut(BaseModel):
    role: str = Field(pattern="^(owner|editor|viewer)$")


class NodeCreate(BaseModel):
    kind: str
    slug: str
    title: str = ""
    content: str = ""
    under: str | None = None  # parent selector; None → graph root
    position: int = 0
    starts: date | None = None
    ends: date | None = None
    icps: list[str] = []  # icp selectors


class NodePatch(BaseModel):
    version: int
    title: str | None = None
    content: str | None = None
    position: int | None = None
    starts: date | None = None
    ends: date | None = None
    icps: list[str] | None = None


class FlywheelPut(BaseModel):
    slug: str = "flywheel"
    title: str = ""
    content: str = ""
    status: str | None = None


class FlywheelNodeCreate(BaseModel):
    slug: str
    title: str = ""
    content: str = ""
    status: str | None = None
    position: int = 0
    next: list[str] = []  # flywheel node selectors (ref, slug, or uuid)


class FlywheelNodePatch(BaseModel):
    title: str | None = None
    content: str | None = None
    status: str | None = None
    position: int | None = None
    next: list[str] | None = None
