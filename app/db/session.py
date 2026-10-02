"""Postgres connection client built on SQLAlchemy 2 + psycopg 3 (synchronous).

Usage in a route (plain `def`, FastAPI runs it in a worker thread):

    @router.get("/items")
    def list_items(db: DBDep) -> list[Item]:
        return db.execute(select(Item)).scalars().all()

Usage outside a request (scripts, jobs):

    with get_db_client().session() as db:
        db.execute(...)
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import URL, Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.exceptions import AppError

logger = logging.getLogger(__name__)


class DatabaseError(AppError):
    status_code = 503
    code = "database_unavailable"


class DatabaseClient:
    """Owns the engine (connection pool) and hands out sessions.

    Construct from parts:
        DatabaseClient(host="localhost", port=5432, database="retail_db",
                       user="datakernuser", password="...")
    or from a ready-made URL:
        DatabaseClient.from_url("postgresql+psycopg://user:pw@host:5432/db")
    """

    def __init__(
        self,
        *,
        host: str,
        port: int = 5432,
        database: str,
        user: str,
        password: str = "",
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: float = 30.0,
        pool_recycle: int = 1800,
        echo: bool = False,
    ) -> None:
        url = URL.create(
            drivername="postgresql+psycopg",
            host=host,
            port=port,
            database=database,
            username=user,
            password=password,
        )
        self._init_engine(
            url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            echo=echo,
        )

    @classmethod
    def from_url(cls, url: str | URL, **pool_kwargs: object) -> "DatabaseClient":
        self = cls.__new__(cls)
        self._init_engine(url, **pool_kwargs)  # type: ignore[arg-type]
        return self

    def _init_engine(
        self,
        url: str | URL,
        *,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: float = 30.0,
        pool_recycle: int = 1800,
        echo: bool = False,
    ) -> None:
        self.engine: Engine = create_engine(
            url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,  # drop dead connections transparently
            echo=echo,
        )
        self._session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Transactional scope: commits on success, rolls back on error, always closes."""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def ping(self) -> bool:
        """Return True if a round-trip to the database succeeds."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError as exc:
            logger.warning("Database ping failed: %s", exc)
            return False

    def dispose(self) -> None:
        """Close all pooled connections. Call on application shutdown."""
        self.engine.dispose()


@lru_cache
def get_db_client() -> DatabaseClient:
    s = get_settings()
    return DatabaseClient(
        host=s.db_host,
        port=s.db_port,
        database=s.db_name,
        user=s.db_user,
        password=s.db_password.get_secret_value(),
        pool_size=s.db_pool_size,
        max_overflow=s.db_max_overflow,
        pool_timeout=s.db_pool_timeout_seconds,
        pool_recycle=s.db_pool_recycle_seconds,
        echo=s.db_echo,
    )


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, committed if the handler succeeds."""
    try:
        with get_db_client().session() as session:
            yield session
    except SQLAlchemyError as exc:
        logger.exception("Database error")
        raise DatabaseError("Database request failed") from exc
