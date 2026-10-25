"""SQLAlchemy session factory for RegImpact-SL.

Provides:
  - create_engine_from_url(): builds an engine from a DATABASE_URL string.
  - get_session_factory(): returns a sessionmaker bound to an engine.
  - get_db(): FastAPI dependency injecting a scoped Session.

The default DATABASE_URL falls back to an in-memory SQLite instance so
all unit tests can run without a live PostgreSQL daemon.
"""

import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

try:
    from dotenv import load_dotenv
    for _p in [
        Path(__file__).resolve().parent.parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent.parent / ".env",
    ]:
        if _p.exists():
            load_dotenv(_p, override=False)
except ImportError:
    pass

from backend.src.db.models import Base

# ---------------------------------------------------------------------------
# Database URL resolution
# ---------------------------------------------------------------------------

_DEFAULT_SQLITE_URL = "sqlite:///:memory:"


def get_database_url() -> str:
    """Return the configured DATABASE_URL, defaulting to SQLite in-memory."""
    return os.environ.get("DATABASE_URL", _DEFAULT_SQLITE_URL)


def create_engine_from_url(url: str | None = None, **kwargs) -> Engine:
    """Create a SQLAlchemy engine from a URL.

    Applies SQLite-specific pragma (foreign_keys = ON) automatically.
    For PostgreSQL the JSON dialect is used as-is.
    """
    resolved_url = url or get_database_url()
    is_sqlite = resolved_url.startswith("sqlite")

    connect_args = kwargs.pop("connect_args", {})
    engine_kwargs = dict(kwargs)
    if is_sqlite:
        # Allow the same in-memory database to be used across threads in tests
        connect_args["check_same_thread"] = False
        if ":memory:" in resolved_url:
            from sqlalchemy.pool import StaticPool
            engine_kwargs["poolclass"] = StaticPool

    engine = create_engine(
        resolved_url,
        connect_args=connect_args,
        echo=False,
        future=True,
        **engine_kwargs,
    )

    if is_sqlite:
        # Enable FK enforcement on every new SQLite connection
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_tables(engine: Engine) -> None:
    """Create all ORM tables on the given engine (idempotent: CREATE IF NOT EXISTS)."""
    is_postgres = "postgresql" in engine.dialect.name
    if is_postgres:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()

    Base.metadata.create_all(bind=engine)

    if is_postgres:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_clauses_embedding_hnsw "
                    "ON clauses USING hnsw (embedding vector_cosine_ops);"
                )
            )
            # Idempotently ensure recent columns exist on pre-existing PostgreSQL databases
            conn.execute(text("ALTER TABLE source_documents ADD COLUMN IF NOT EXISTS is_synthetic BOOLEAN NOT NULL DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE clauses ADD COLUMN IF NOT EXISTS is_synthetic BOOLEAN NOT NULL DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE clauses ADD COLUMN IF NOT EXISTS embedding_verified BOOLEAN NOT NULL DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE clauses ADD COLUMN IF NOT EXISTS embedding_provider VARCHAR(50);"))
            conn.execute(text("ALTER TABLE clauses ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(100);"))
            conn.execute(text("ALTER TABLE rules ADD COLUMN IF NOT EXISTS is_synthetic BOOLEAN NOT NULL DEFAULT FALSE;"))
            conn.commit()


def get_session_factory(engine: Engine) -> sessionmaker:
    """Return a sessionmaker bound to *engine*."""
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


# ---------------------------------------------------------------------------
# Application-level singleton (lazily initialised)
# ---------------------------------------------------------------------------

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


import logging

logger = logging.getLogger(__name__)


def init_db(url: str | None = None) -> Engine:
    """Initialise the global engine and session factory; create tables.

    Safe to call multiple times – subsequent calls are no-ops unless *url*
    differs from the current engine's URL.
    """
    global _engine, _SessionLocal
    resolved_url = url or get_database_url()

    if "postgresql" in resolved_url.lower():
        try:
            check_engine = create_engine_from_url(resolved_url, connect_args={"connect_timeout": 1})
            with check_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:
            logger.warning(
                "PostgreSQL daemon unreachable at %s (%s); falling back to SQLite storage.",
                resolved_url,
                exc,
            )
            resolved_url = _DEFAULT_SQLITE_URL

    if _engine is None or str(_engine.url) != resolved_url:
        _engine = create_engine_from_url(resolved_url)
        _SessionLocal = get_session_factory(_engine)
        create_tables(_engine)

    return _engine


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a database Session and close it afterwards.

    Usage in a route::

        @app.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    if _SessionLocal is None:
        init_db()
    session: Session = _SessionLocal()  # type: ignore[misc]
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def session_scope(engine: Engine | None = None) -> Generator[Session, None, None]:
    """Context-manager wrapping a transactional session.

    Useful in scripts and CLI ingestion commands that are not inside the
    FastAPI request/response lifecycle.
    """
    if engine is None:
        if _engine is None:
            init_db()
        engine = _engine

    factory = get_session_factory(engine)
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
