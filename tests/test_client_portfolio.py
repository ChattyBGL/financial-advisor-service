import json
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import DatabaseClient
from app.services.client_portfolio import SCHEMA as SCHEMA_NAME
from app.services.client_portfolio import load_client_portfolio
from app.services.context import ContextService

# SQLite has no schemas; attaching a second in-memory database under the same
# name lets the `advisory.table` references in the real query resolve.
SCHEMA = f"""
ATTACH DATABASE ':memory:' AS {SCHEMA_NAME};
CREATE TABLE {SCHEMA_NAME}.clients (
    client_id INTEGER PRIMARY KEY, first_name VARCHAR(50), last_name VARCHAR(50),
    email VARCHAR(100), risk_tolerance VARCHAR(20));
CREATE TABLE {SCHEMA_NAME}.portfolios (
    portfolio_id INTEGER PRIMARY KEY, client_id INT REFERENCES clients(client_id),
    cash_balance DECIMAL(15,2), total_value DECIMAL(15,2));
CREATE TABLE {SCHEMA_NAME}.portfolio_holdings (
    holding_id INTEGER PRIMARY KEY, portfolio_id INT REFERENCES portfolios(portfolio_id),
    ticker VARCHAR(10), shares INT, average_buy_price DECIMAL(10,2));
INSERT INTO {SCHEMA_NAME}.clients VALUES (1, 'Ada', 'Lovelace', 'ada@example.com', 'moderate');
INSERT INTO {SCHEMA_NAME}.clients VALUES (2, 'Nobody', 'Empty', 'none@example.com', 'low');
INSERT INTO {SCHEMA_NAME}.portfolios VALUES (10, 1, 2500.50, 18250.00);
INSERT INTO {SCHEMA_NAME}.portfolios VALUES (11, 1, 100.00, 100.00);
INSERT INTO {SCHEMA_NAME}.portfolio_holdings VALUES (100, 10, 'AAPL', 20, 150.25);
INSERT INTO {SCHEMA_NAME}.portfolio_holdings VALUES (101, 10, 'MSFT', 10, 300.00);
"""


@pytest.fixture
def db() -> Iterator[DatabaseClient]:
    client = DatabaseClient.__new__(DatabaseClient)
    client.engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    client._session_factory = sessionmaker(bind=client.engine, expire_on_commit=False)
    with client.session() as s:
        for stmt in filter(None, (x.strip() for x in SCHEMA.split(";"))):
            s.execute(text(stmt))
    yield client
    client.dispose()


def test_load_client_with_portfolios_and_holdings(db: DatabaseClient) -> None:
    assert load_client_portfolio(db, 1) == {
        "client_name": "Ada Lovelace",
        "risk_tolerance": "moderate",
        "portfolios": [
            {
                "cash_balance": 2500.5,
                "total_value": 18250.0,
                "holdings": [
                    {"ticker": "AAPL", "shares": 20, "average_buy_price": 150.25},
                    {"ticker": "MSFT", "shares": 10, "average_buy_price": 300.0},
                ],
            },
            {"cash_balance": 100.0, "total_value": 100.0, "holdings": []},
        ],
    }


def test_client_without_portfolios(db: DatabaseClient) -> None:
    client = load_client_portfolio(db, 2)
    assert client is not None
    assert client["client_name"] == "Nobody Empty"
    assert client["portfolios"] == []


def test_missing_client_is_none(db: DatabaseClient) -> None:
    assert load_client_portfolio(db, 999) is None


def test_context_is_json_and_uses_client_name_not_id(db: DatabaseClient) -> None:
    ctx = ContextService(
        sources={"client_portfolio": lambda _p, client: client},
        load_client=lambda cid: load_client_portfolio(db, cid),
    )
    out = ctx.build("how risky am I?", client_id=1)
    assert out.client_name == "Ada Lovelace"
    assert out.data["client_portfolio"]["client_name"] == "Ada Lovelace"
    assert "client_id" not in json.dumps(out.data)
    json.dumps(out.data)  # must be serialisable as-is

    assert ctx.build("how risky am I?", client_id=None).data == {}
    unknown = ctx.build("how risky am I?", client_id=999)
    assert unknown.data == {} and unknown.client_name is None
