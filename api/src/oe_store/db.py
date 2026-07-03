"""Engine/session setup and startup migrations."""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_URL = "postgresql+psycopg://oe:oe@localhost:5432/oe"


def database_url() -> str:
    return os.environ.get("OE_DATABASE_URL", DEFAULT_DATABASE_URL)


def make_engine(url: str | None = None):
    return create_engine(url or database_url(), pool_pre_ping=True)


def make_session_factory(engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def run_migrations(url: str | None = None) -> None:
    """Upgrade the schema to head; called on API startup."""
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    config.set_main_option("sqlalchemy.url", url or database_url())
    command.upgrade(config, "head")
