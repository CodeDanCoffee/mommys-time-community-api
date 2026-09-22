from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..database import get_session
from ..models import Block, User
from ..security import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/{user_id}/block", status_code=status.HTTP_201_CREATED)
def block_user(
    user_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Block another user — their threads and replies stop showing for you."""
    if user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can't block yourself",
        )
    if session.get(User, user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    existing = session.exec(
        select(Block).where(Block.blocker_id == user.id, Block.blocked_id == user_id)
    ).first()
    if existing is None:
        session.add(Block(blocker_id=user.id, blocked_id=user_id))
        session.commit()
    return {"status": "blocked"}


@router.delete("/{user_id}/block", status_code=status.HTTP_204_NO_CONTENT)
def unblock_user(
    user_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Undo a block."""
    existing = session.exec(
        select(Block).where(Block.blocker_id == user.id, Block.blocked_id == user_id)
    ).first()
    if existing is not None:
        session.delete(existing)
        session.commit()
