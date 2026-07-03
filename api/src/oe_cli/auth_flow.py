"""Browser-based OIDC login for the CLI.

Uses the OAuth device-authorization flow: `oe login` prints/opens a
verification URL, polls the token endpoint, and stores tokens in
~/.config/oe/. Provider settings come from env or saved config:

- OE_OIDC_ISSUER (discovery via /.well-known/openid-configuration)
- OE_OIDC_CLIENT_ID
- OE_OIDC_AUDIENCE (optional)

For simulation-mode servers, `oe login --token <name>` stores a plain token.
"""

from __future__ import annotations

import os
import time
import webbrowser

import httpx

from oe_cli import config


class LoginError(Exception):
    pass


def _provider_settings() -> dict:
    saved = config.load_config()
    issuer = os.environ.get("OE_OIDC_ISSUER") or saved.get("oidc_issuer")
    client_id = os.environ.get("OE_OIDC_CLIENT_ID") or saved.get("oidc_client_id")
    audience = os.environ.get("OE_OIDC_AUDIENCE") or saved.get("oidc_audience")
    if not issuer or not client_id:
        raise LoginError(
            "OIDC login needs OE_OIDC_ISSUER and OE_OIDC_CLIENT_ID (env or saved config). "
            "Against a simulation-mode server, use `oe login --token <name>` instead."
        )
    return {"issuer": issuer.rstrip("/"), "client_id": client_id, "audience": audience}


def _discover(issuer: str) -> dict:
    response = httpx.get(f"{issuer}/.well-known/openid-configuration", timeout=15)
    response.raise_for_status()
    return response.json()


def device_login(*, open_browser: bool = True, echo=print) -> None:
    provider = _provider_settings()
    metadata = _discover(provider["issuer"])
    device_endpoint = metadata.get("device_authorization_endpoint")
    if not device_endpoint:
        raise LoginError("provider does not support the device-authorization flow")

    payload = {"client_id": provider["client_id"], "scope": "openid profile email offline_access"}
    if provider["audience"]:
        payload["audience"] = provider["audience"]
    started = httpx.post(device_endpoint, data=payload, timeout=15)
    started.raise_for_status()
    device = started.json()

    url = device.get("verification_uri_complete") or device["verification_uri"]
    echo(f"Confirm code {device['user_code']} at: {url}")
    if open_browser:
        webbrowser.open(url)

    tokens = _poll_for_tokens(metadata["token_endpoint"], provider["client_id"], device)
    _store_tokens(tokens, provider)
    echo("Logged in.")


def _poll_for_tokens(token_endpoint: str, client_id: str, device: dict) -> dict:
    interval = device.get("interval", 5)
    deadline = time.monotonic() + device.get("expires_in", 300)
    while time.monotonic() < deadline:
        time.sleep(interval)
        response = httpx.post(
            token_endpoint,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device["device_code"],
                "client_id": client_id,
            },
            timeout=15,
        )
        body = response.json()
        if response.status_code == 200:
            return body
        error = body.get("error")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5
            continue
        raise LoginError(f"login failed: {body.get('error_description', error)}")
    raise LoginError("login timed out; try again")


def _store_tokens(tokens: dict, provider: dict) -> None:
    saved = config.load_config()
    saved.update(
        {
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "oidc_issuer": provider["issuer"],
            "oidc_client_id": provider["client_id"],
            "oidc_audience": provider["audience"],
        }
    )
    config.save_config(saved)


def refresh_tokens() -> bool:
    """Try to refresh the stored access token; True on success."""
    saved = config.load_config()
    refresh_token = saved.get("refresh_token")
    issuer = saved.get("oidc_issuer")
    client_id = saved.get("oidc_client_id")
    if not refresh_token or not issuer or not client_id:
        return False
    try:
        metadata = _discover(issuer)
        response = httpx.post(
            metadata["token_endpoint"],
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
            },
            timeout=15,
        )
        if response.status_code != 200:
            return False
        tokens = response.json()
    except httpx.HTTPError:
        return False
    saved["access_token"] = tokens["access_token"]
    if tokens.get("refresh_token"):
        saved["refresh_token"] = tokens["refresh_token"]
    config.save_config(saved)
    return True


def store_plain_token(token: str) -> None:
    saved = config.load_config()
    saved["access_token"] = token
    saved.pop("refresh_token", None)
    config.save_config(saved)


def logout() -> None:
    saved = config.load_config()
    for key in ("access_token", "refresh_token"):
        saved.pop(key, None)
    config.save_config(saved)
