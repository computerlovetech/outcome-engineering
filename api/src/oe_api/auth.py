"""Identity resolution: JWT bearer (oidc or simulation mode) or share token.

Every request resolves to a Principal: an authenticated User, a share-token
viewer scoped to one graph, or anonymous (rejected by the dependencies that
require identity).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request

from oe_api.db import get_store
from oe_api.settings import Settings, get_settings
from oe_store.models import User
from oe_store.store import GraphStore

_jwks_clients: dict[str, jwt.PyJWKClient] = {}


@dataclass
class Principal:
    user: User | None = None
    share_graph_id: uuid.UUID | None = None  # set when access came via share token

    @property
    def is_authenticated(self) -> bool:
        return self.user is not None


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return None


def _share_token(request: Request) -> str | None:
    return request.headers.get("X-Share-Token") or request.query_params.get("share")


def _decode_oidc_token(token: str, settings: Settings) -> dict:
    if not settings.oidc_jwks_url:
        raise HTTPException(status_code=500, detail="OE_OIDC_JWKS_URL is not configured")
    client = _jwks_clients.get(settings.oidc_jwks_url)
    if client is None:
        client = jwt.PyJWKClient(settings.oidc_jwks_url)
        _jwks_clients[settings.oidc_jwks_url] = client
    try:
        signing_key = client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.oidc_audience or None,
            issuer=settings.oidc_issuer or None,
            options={"verify_aud": bool(settings.oidc_audience)},
        )
    except jwt.PyJWTError as error:
        raise HTTPException(status_code=401, detail=f"invalid token: {error}") from error


def get_principal(
    request: Request,
    store: GraphStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> Principal:
    token = _bearer_token(request)
    if token is not None:
        if settings.auth_mode == "simulation":
            # Simulation mode: the bearer token IS the dev identity, so local
            # setups can act as multiple users ("dev", "alice", ...).
            user = store.upsert_user(
                oidc_subject=f"simulation|{token}",
                email=f"{token}@simulated.local",
                name=token,
            )
        else:
            claims = _decode_oidc_token(token, settings)
            subject = claims.get("sub")
            if not subject:
                raise HTTPException(status_code=401, detail="token has no sub claim")
            user = store.upsert_user(
                oidc_subject=subject,
                email=claims.get(settings.oidc_email_claim),
                name=claims.get(settings.oidc_name_claim),
            )
        store.session.commit()
        return Principal(user=user)

    share = _share_token(request)
    if share is not None:
        link = store.find_share_token(share)
        if link is None:
            raise HTTPException(status_code=401, detail="share token is invalid or revoked")
        return Principal(share_graph_id=link.graph_id)

    return Principal()


def require_user(principal: Principal = Depends(get_principal)) -> User:
    if principal.user is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return principal.user
