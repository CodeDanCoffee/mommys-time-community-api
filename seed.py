"""Insert a few sample discussions so the API isn't an empty room in dev.

Run:  python seed.py
Safe to run repeatedly — it only seeds when the threads table is empty.
"""
from sqlmodel import Session, select

from app.database import engine, init_db
from app.models import Reply, Thread, User


def _user(session: Session, apple_sub: str, name: str) -> User:
    user = session.exec(select(User).where(User.apple_sub == apple_sub)).first()
    if user is None:
        user = User(apple_sub=apple_sub, display_name=name)
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def run() -> None:
    init_db()
    with Session(engine) as session:
        if session.exec(select(Thread)).first() is not None:
            print("Threads already exist — skipping seed.")
            return

        aina = _user(session, "dev-aina", "Aina")
        suraya = _user(session, "dev-suraya", "Suraya")
        mei = _user(session, "dev-mei", "Mei")

        t1 = Thread(
            author_id=aina.id,
            topic="Nights",
            title="Third night in a row of 3am wake-ups",
            body="Just need to say it out loud to people who get it.",
        )
        t2 = Thread(
            author_id=suraya.id,
            topic="Feeding",
            title="Starting solids — where do I even begin?",
            body="Baby is 6 months. Feeling a little overwhelmed by all the advice.",
        )
        session.add(t1)
        session.add(t2)
        session.commit()
        session.refresh(t1)

        session.add(Reply(thread_id=t1.id, author_id=suraya.id, body="Sending you a hug. You're doing so well."))
        session.add(Reply(thread_id=t1.id, author_id=mei.id, body="Same here tonight. We've got this."))
        session.commit()
        print("Seeded sample threads.")


if __name__ == "__main__":
    run()
