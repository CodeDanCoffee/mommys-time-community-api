from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlmodel import Session

from .config import settings
from .database import get_session
from .models import User

# Apple publishes its public keys here; PyJWKClient fetches + caches them.
_jwks_client = PyJWKClient(settings.apple_jwks_url)


def verify_apple_identity_token(identity_token: str) -> dict:
    """Verify Apple's identity token (signature, audience, issuer, expiry).

    Returns the decoded claims, which include `sub` (the stable Apple user id)
    and often `email`. Raises 401 on any problem.
    """
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(identity_token)
        return jwt.decode(
            identity_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.apple_bundle_id,
            issuer=settings.apple_issuer,
        )
    except Exception as exc:  # noqa: BLE001 - surface a clean 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Apple identity token: {exc}",
        )


def create_access_token(user_id: str) -> str:
    """Issue one of OUR session tokens for an authenticated user."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(days=settings.session_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _user_from_token(token: str, session: Session) -> Optional[User]:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except Exception:  # noqa: BLE001
        return None
    return session.get(User, payload.get("sub"))


_required_bearer = HTTPBearer(auto_error=True)
_optional_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_required_bearer),
    session: Session = Depends(get_session),
) -> User:
    """Require a valid session token; return the signed-in user."""
    user = _user_from_token(creds.credentials, session)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
        )
    return user


def get_optional_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_optional_bearer),
    session: Session = Depends(get_session),
) -> Optional[User]:
    """Return the user if a valid token is present, else None (for public GETs
    that still want to know 'did *I* hug this?')."""
    if creds is None:
        return None
    return _user_from_token(creds.credentials, session)
