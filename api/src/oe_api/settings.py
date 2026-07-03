"""API settings, all env-configurable with sane localhost defaults."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OE_")

    database_url: str = "postgresql+psycopg://oe:oe@localhost:5432/oe"
    # "simulation" injects a fake dev user (no provider needed); "oidc" validates
    # JWTs against the provider's JWKS.
    auth_mode: str = "simulation"
    oidc_issuer: str = ""
    oidc_jwks_url: str = ""
    oidc_audience: str = ""
    # Claims used to populate users rows.
    oidc_email_claim: str = "email"
    oidc_name_claim: str = "name"
    run_migrations_on_startup: bool = True
    # Comma-separated list of allowed browser origins (the frontend URL).
    cors_origins: str = "*"


@lru_cache
def get_settings() -> Settings:
    return Settings()
