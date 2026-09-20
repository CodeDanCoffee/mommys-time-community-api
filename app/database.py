from sqlmodel import SQLModel, Session, create_engine

from .config import settings

# SQLite needs this flag when used across FastAPI's threads.
connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def init_db() -> None:
    """Create tables. Imported models must be loaded first."""
    from . import models  # noqa: F401  (ensures models are registered)

    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
