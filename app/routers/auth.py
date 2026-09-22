from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..config import settings
from ..database import get_session
from ..models import Block, Hug, Reply, Thread, User
from ..schemas import AppleLoginRequest, AuthResponse, UpdateMeRequest, UserOut
from ..security import create_access_token, get_current_user, verify_apple_identity_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/apple", response_model=AuthResponse)
def sign_in_with_apple(req: AppleLoginRequest, session: Session = Depends(get_session)):
    """Exchange an Apple identity token for one of our session tokens.

    Creates the user on first sign-in, then returns a bearer token the app
    sends on every subsequent request so we know who's posting.
    """
    email = req.email

    # In dev, prefer the dev shortcut when supplied — so the Swagger form's
    # leftover `"identity_token": "string"` placeholder is harmless.
    if settings.allow_dev_login and req.dev_apple_sub:
        apple_sub = req.dev_apple_sub
    elif req.identity_token:
        claims = verify_apple_identity_token(req.identity_token)
        apple_sub = claims["sub"]
        email = claims.get("email") or email
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


@router.put("/me", response_model=UserOut, tags=["auth"])
def update_me(
    req: UpdateMeRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Update the signed-in user's display name. Author names are resolved live,
    so this also fixes the name on the user's existing posts and replies."""
    name = req.display_name.strip()
    if name:
        user.display_name = name
        session.add(user)
        session.commit()
        session.refresh(user)
    return UserOut(id=user.id, display_name=user.display_name, email=user.email)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, tags=["auth"])
def delete_me(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Permanently delete the signed-in user and everything they created:
    their threads (with those threads' replies and hugs), their replies and
    hugs on others' threads, and their reports and blocks."""
    uid = user.id

    # Threads authored by the user — remove dependent replies/hugs first.
    own_threads = session.exec(select(Thread).where(Thread.author_id == uid)).all()
    for thread in own_threads:
        for reply in session.exec(select(Reply).where(Reply.thread_id == thread.id)).all():
            session.delete(reply)
        for hug in session.exec(select(Hug).where(Hug.thread_id == thread.id)).all():
            session.delete(hug)
        session.delete(thread)

    # The user's own replies/hugs on other people's threads.
    for reply in session.exec(select(Reply).where(Reply.author_id == uid)).all():
        session.delete(reply)
    for hug in session.exec(select(Hug).where(Hug.user_id == uid)).all():
        session.delete(hug)

    # Blocks in either direction.
    for block in session.exec(
        select(Block).where(
            (Block.blocker_id == uid) | (Block.blocked_id == uid)
        )
    ).all():
        session.delete(block)

    session.delete(user)
    session.commit()
