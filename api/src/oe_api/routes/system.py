from __future__ import annotations

from fastapi import APIRouter, Depends

from oe_api.auth import require_user
from oe_store.models import User

router = APIRouter()


@router.get("/system/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/me")
def me(user: User = Depends(require_user)) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "oidcSubject": user.oidc_subject,
    }
