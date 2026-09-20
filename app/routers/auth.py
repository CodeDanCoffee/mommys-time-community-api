from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..config import settings
from ..database import get_session
from ..models import User
from ..schemas import AppleLoginRequest, AuthResponse, UserOut
from ..security import create_access_token, get_current_user, verify_apple_identity_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/apple", response_model=AuthResponse)
def sign_in_with_apple(req: AppleLoginRequest, session: Session = Depends(get_session)):
    """Exchange an Apple identity token for one of our session tokens.

    Creates the user on first sign-in, then returns a bearer token the app
    sends on every subsequent request so we know who's posting.
    """
    email = req.email

    if req.identity_token:
        claims = verify_apple_identity_token(req.identity_token)
        apple_sub = claims["sub"]
        email = claims.get("email") or email
    elif settings.allow_dev_login and req.dev_apple_sub:
        # Dev shortcut only — never trusts an unverified id in production.
        apple_sub = req.dev_apple_sub
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="identity_token is required",
        )

    user = session.exec(select(User).where(User.apple_sub == apple_sub)).first()
    if user is None:
        user = User(
            apple_sub=apple_sub,
            display_name=(req.full_name or "Mama").strip() or "Mama",
            email=email,
        )
        session.add(user)
    else:
        # Apple only sends name/email on the first sign-in, so backfill if we
        # never captured them.
        if req.full_name and user.display_name in (None, "", "Mama"):
            user.display_name = req.full_name.strip()
        if email and not user.email:
            user.email = email
        session.add(user)

    session.commit()
    session.refresh(user)

    token = create_access_token(user.id)
    return AuthResponse(
        access_token=token,
        user=UserOut(id=user.id, display_name=user.display_name, email=user.email),
    )


@router.get("/me", response_model=UserOut, tags=["auth"])
def me(user: User = Depends(get_current_user)):
    return UserOut(id=user.id, display_name=user.display_name, email=user.email)
