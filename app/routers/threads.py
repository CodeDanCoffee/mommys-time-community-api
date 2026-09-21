from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from ..database import get_session
from ..models import Hug, Reply, Thread, User
from ..schemas import (
    MAX_TOPIC_LENGTH,
    ReplyCreate,
    ReplyOut,
    ThreadCreate,
    ThreadDetailOut,
    ThreadOut,
)
from ..security import get_current_user, get_optional_user

router = APIRouter(prefix="/threads", tags=["threads"])


# ---- helpers ----

def _author_name(session: Session, author_id: str) -> str:
    author = session.get(User, author_id)
    return author.display_name if author else "Mama"


def _thread_out(session: Session, thread: Thread, viewer: Optional[User]) -> ThreadOut:
    reply_count = session.scalar(
        select(func.count()).select_from(Reply).where(Reply.thread_id == thread.id)
    )
    hug_count = session.scalar(
        select(func.count()).select_from(Hug).where(Hug.thread_id == thread.id)
    )
    hugged = False
    if viewer is not None:
        hugged = (
            session.exec(
                select(Hug).where(
                    Hug.user_id == viewer.id, Hug.thread_id == thread.id
                )
            ).first()
            is not None
        )
    return ThreadOut(
        id=thread.id,
        topic=thread.topic,
        title=thread.title,
        body=thread.body,
        author=_author_name(session, thread.author_id),
        author_id=thread.author_id,
        created_at=thread.created_at,
        reply_count=int(reply_count or 0),
        hug_count=int(hug_count or 0),
        hugged=hugged,
        is_mine=(viewer is not None and viewer.id == thread.author_id),
    )


def _reply_out(session: Session, reply: Reply, viewer: Optional[User]) -> ReplyOut:
    return ReplyOut(
        id=reply.id,
        body=reply.body,
        author=_author_name(session, reply.author_id),
        author_id=reply.author_id,
        created_at=reply.created_at,
        is_mine=(viewer is not None and viewer.id == reply.author_id),
    )


def _get_thread_or_404(session: Session, thread_id: str) -> Thread:
    thread = session.get(Thread, thread_id)
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return thread


# ---- endpoints ----

@router.get("", response_model=List[ThreadOut])
def list_threads(
    topic: Optional[str] = None,
    session: Session = Depends(get_session),
    viewer: Optional[User] = Depends(get_optional_user),
):
    """All discussions, newest first. Optional `?topic=` filter."""
    query = select(Thread).order_by(Thread.created_at.desc())
    if topic:
        query = query.where(Thread.topic == topic)
    threads = session.exec(query).all()
    return [_thread_out(session, t, viewer) for t in threads]


@router.post("", response_model=ThreadOut, status_code=status.HTTP_201_CREATED)
def create_thread(
    payload: ThreadCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    topic = payload.topic.strip()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="topic is required",
        )
    if len(topic) > MAX_TOPIC_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"topic must be {MAX_TOPIC_LENGTH} characters or fewer",
        )
    if not payload.title.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="title is required",
        )
    thread = Thread(
        author_id=user.id,
        topic=topic,
        title=payload.title.strip(),
        body=payload.body.strip(),
    )
    session.add(thread)
    session.commit()
    session.refresh(thread)
    return _thread_out(session, thread, user)


@router.get("/{thread_id}", response_model=ThreadDetailOut)
def get_thread(
    thread_id: str,
    session: Session = Depends(get_session),
    viewer: Optional[User] = Depends(get_optional_user),
):
    thread = _get_thread_or_404(session, thread_id)
    base = _thread_out(session, thread, viewer)
    replies = session.exec(
        select(Reply)
        .where(Reply.thread_id == thread_id)
        .order_by(Reply.created_at.asc())
    ).all()
    return ThreadDetailOut(
        **base.model_dump(),
        replies=[_reply_out(session, r, viewer) for r in replies],
    )


@router.post(
    "/{thread_id}/replies",
    response_model=ReplyOut,
    status_code=status.HTTP_201_CREATED,
)
def add_reply(
    thread_id: str,
    payload: ReplyCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _get_thread_or_404(session, thread_id)
    if not payload.body.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="body is required",
        )
    reply = Reply(thread_id=thread_id, author_id=user.id, body=payload.body.strip())
    session.add(reply)
    session.commit()
    session.refresh(reply)
    return _reply_out(session, reply, user)


@router.post("/{thread_id}/hug", response_model=ThreadOut)
def toggle_hug(
    thread_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Add or remove the current user's hug on a thread."""
    thread = _get_thread_or_404(session, thread_id)
    existing = session.exec(
        select(Hug).where(Hug.user_id == user.id, Hug.thread_id == thread_id)
    ).first()
    if existing is not None:
        session.delete(existing)
    else:
        session.add(Hug(user_id=user.id, thread_id=thread_id))
    session.commit()
    return _thread_out(session, thread, user)


@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_thread(
    thread_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Delete a thread you started (and its replies + hugs)."""
    thread = _get_thread_or_404(session, thread_id)
    if thread.author_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own thread",
        )
    for reply in session.exec(select(Reply).where(Reply.thread_id == thread_id)).all():
        session.delete(reply)
    for hug in session.exec(select(Hug).where(Hug.thread_id == thread_id)).all():
        session.delete(hug)
    session.delete(thread)
    session.commit()


@router.delete("/replies/{reply_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reply(
    reply_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    reply = session.get(Reply, reply_id)
    if reply is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reply not found")
    if reply.author_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own reply",
        )
    session.delete(reply)
    session.commit()
