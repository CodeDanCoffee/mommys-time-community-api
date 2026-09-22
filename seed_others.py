"""Seed a few discussions from OTHER users, so you can test Report/Block.

Unlike seed.py (which only runs on an empty DB), this always tops up the
sample content — but it won't duplicate posts it already added.

Run on the server, with the same Python that runs the app, e.g.:
    cd /path/to/mommys-time-community-api
    .venv/bin/python seed_others.py
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


# (author apple_sub, author name, topic, title, body, [replies])
SEEDS = [
    ("seed-suraya", "Suraya", "Feeding", "Combo feeding — any tips?",
     "Started combining breast and formula this week. What worked for you mamas?",
     ["Slow and steady worked for us — you've got this."]),
    ("seed-mei", "Mei", "Nights", "3am wake-ups again",
     "Third night in a row. Just need some solidarity tonight.",
     ["Sending hugs. It does pass, promise."]),
    ("seed-hana", "Hana", "Me-time", "How do you find 10 minutes for yourself?",
     "Genuinely asking — where does everyone hide for a quiet cup of tea?",
     []),
]


def run() -> None:
    init_db()
    added = 0
    with Session(engine) as session:
        for apple_sub, name, topic, title, body, replies in SEEDS:
            # Skip if this exact post already exists (idempotent).
            if session.exec(select(Thread).where(Thread.title == title)).first():
                continue
            author = _user(session, apple_sub, name)
            thread = Thread(author_id=author.id, topic=topic, title=title, body=body)
            session.add(thread)
            session.commit()
            session.refresh(thread)
            for text in replies:
                replier = _user(session, "seed-aina", "Aina")
                session.add(Reply(thread_id=thread.id, author_id=replier.id, body=text))
            session.commit()
            added += 1
    print(f"Seeded {added} new discussion(s) from other users.")


if __name__ == "__main__":
    run()
