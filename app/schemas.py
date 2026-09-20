from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

# Topics must stay in sync with the iOS app's VillageTopic raw values.
ALLOWED_TOPICS = {"Nights", "Feeding", "Me-time"}


# ---- Auth ----

class AppleLoginRequest(BaseModel):
    """What the iOS app posts after a successful Sign in with Apple.

    Send `identity_token` (the JWT from ASAuthorizationAppleIDCredential).
    `full_name` / `email` are only present on the very first sign-in.
    `dev_apple_sub` is a dev-only shortcut (needs ALLOW_DEV_LOGIN=true).
    """

    identity_token: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    dev_apple_sub: Optional[str] = None


class UserOut(BaseModel):
    id: str
    display_name: str
    email: Optional[str] = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---- Threads & replies ----

class ThreadCreate(BaseModel):
    topic: str
    title: str
    body: str = ""


class ReplyCreate(BaseModel):
    body: str


class ReplyOut(BaseModel):
    id: str
    body: str
    author: str
    author_id: str
    created_at: datetime
    is_mine: bool = False


class ThreadOut(BaseModel):
    id: str
    topic: str
    title: str
    body: str
    author: str
    author_id: str
    created_at: datetime
    reply_count: int
    hug_count: int
    hugged: bool = False
    is_mine: bool = False


class ThreadDetailOut(ThreadOut):
    replies: List[ReplyOut] = []
