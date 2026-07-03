"""Thin HTTP client for the Outcome Engineering API."""

from __future__ import annotations

import httpx
import typer

from oe_cli import config
from oe_cli.auth_flow import refresh_tokens


class ApiError(Exception):
    pass


def _request(method: str, path: str, *, retry_auth: bool = True, **kwargs) -> httpx.Response:
    token = config.access_token()
    if token is None:
        raise ApiError("not logged in; run `oe login` (or set OE_TOKEN)")
    response = httpx.request(
        method,
        config.api_url().rstrip("/") + path,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
        **kwargs,
    )
    if response.status_code == 401 and retry_auth and refresh_tokens():
        return _request(method, path, retry_auth=False, **kwargs)
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise ApiError(f"{response.status_code}: {detail}")
    return response


def get(path: str, **kwargs) -> dict:
    return _request("GET", path, **kwargs).json()


def die(error: Exception) -> None:
    typer.secho(str(error), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)
