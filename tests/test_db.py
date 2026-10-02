from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import DatabaseClient, get_db_client
from app.main import create_app


@pytest.fixture
def sqlite_client() -> Iterator[DatabaseClient]:
    """Real DatabaseClient against in-memory SQLite: exercises the session logic
    without needing Postgres in CI."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    client = DatabaseClient.__new__(DatabaseClient)
    client.engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    client._session_factory = sessionmaker(bind=client.engine, expire_on_commit=False)
    yield client
    client.dispose()


def test_session_commits_on_success(sqlite_client: DatabaseClient) -> None:
    with sqlite_client.session() as db:
        db.execute(text("CREATE TABLE t (x INTEGER)"))
        db.execute(text("INSERT INTO t VALUES (1)"))
    with sqlite_client.session() as db:
        assert db.execute(text("SELECT count(*) FROM t")).scalar_one() == 1


def test_session_rolls_back_on_error(sqlite_client: DatabaseClient) -> None:
    with sqlite_client.session() as db:
        db.execute(text("CREATE TABLE t (x INTEGER)"))
    with pytest.raises(RuntimeError), sqlite_client.session() as db:
        db.execute(text("INSERT INTO t VALUES (1)"))
        raise RuntimeError("boom")
    with sqlite_client.session() as db:
        assert db.execute(text("SELECT count(*) FROM t")).scalar_one() == 0


def test_ping(sqlite_client: DatabaseClient) -> None:
    assert sqlite_client.ping() is True


def _app_with_db(ping_result: bool) -> TestClient:
    fake = MagicMock(spec=DatabaseClient)
    fake.ping.return_value = ping_result
    app = create_app()
    app.dependency_overrides[get_db_client] = lambda: fake
    return TestClient(app)


def test_ready_ok_when_db_up() -> None:
    resp = _app_with_db(True).get("/api/v1/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "database": "up"}


def test_ready_503_when_db_down() -> None:
    resp = _app_with_db(False).get("/api/v1/health/ready")
    assert resp.status_code == 503
    assert resp.json() == {"status": "degraded", "database": "down"}


def test_url_is_built_from_parts_and_escapes_password() -> None:
    client = DatabaseClient(
        host="db.example", port=5433, database="retail", user="svc", password="p@ss:w/rd"
    )
    url = client.engine.url
    assert (url.host, url.port, url.database, url.username) == ("db.example", 5433, "retail", "svc")
    assert url.password == "p@ss:w/rd"
    assert url.drivername == "postgresql+psycopg"
    client.dispose()
