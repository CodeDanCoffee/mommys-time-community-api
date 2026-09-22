from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    """One row per Apple account. `apple_sub` is Apple's stable user id."""

    __tablename__ = "users"

    id: str = Field(default_factory=_uuid, primary_key=True)
    apple_sub: str = Field(index=True, unique=True)
    display_name: str = "Mama"
    email: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


class Thread(SQLModel, table=True):
    """A discussion started by a user."""

    __tablename__ = "threads"

    id: str = Field(default_factory=_uuid, primary_key=True)
    author_id: str = Field(foreign_key="users.id", index=True)
    topic: str = Field(index=True)
    title: str
    body: str = ""
    created_at: datetime = Field(default_factory=_now, index=True)


class Reply(SQLModel, table=True):
    """A reply on a thread."""

    __tablename__ = "replies"

    id: str = Field(default_factory=_uuid, primary_key=True)
    thread_id: str = Field(foreign_key="threads.id", index=True)
    author_id: str = Field(foreign_key="users.id", index=True)
    body: str
    created_at: datetime = Field(default_factory=_now, index=True)


class Hug(SQLModel, table=True):
    """A user's 'hug' on a thread — the community's version of a like.

    Composite primary key so a user can hug a thread at most once.
    """

    __tablename__ = "hugs"

    user_id: str = Field(foreign_key="users.id", primary_key=True)
    thread_id: str = Field(foreign_key="threads.id", primary_key=True)
    created_at: datetime = Field(default_factory=_now)


class Report(SQLModel, table=True):
    """A user's report of objectionable content. Reviewed by us out-of-band."""

    __tablename__ = "reports"

    id: str = Field(default_factory=_uuid, primary_key=True)
    reporter_id: str = Field(foreign_key="users.id", index=True)
    # What was reported: a "thread" or a "reply", plus its id.
    target_type: str
    target_id: str = Field(index=True)
    reason: str = ""
    created_at: datetime = Field(default_factory=_now)


class Block(SQLModel, table=True):
    """One user blocking another — the blocker no longer sees their content.

    Composite primary key so the same block can't be recorded twice.
    """

    __tablename__ = "blocks"

    blocker_id: str = Field(foreign_key="users.id", primary_key=True)
    blocked_id: str = Field(foreign_key="users.id", primary_key=True)
    created_at: datetime = Field(default_factory=_now)
