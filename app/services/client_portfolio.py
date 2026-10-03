"""Context source: a client's profile, portfolios and holdings from Postgres.

The client is looked up by id once; the returned data identifies the client
by name only, so the id never reaches the LLM.
"""

from decimal import Decimal
from typing import Any

from sqlalchemy import text

from app.db.session import DatabaseClient

SCHEMA = "advisory"  # Postgres schema that holds clients / portfolios / portfolio_holdings

PROFILE_SQL = text(f"""
    SELECT c.first_name, c.last_name, c.risk_tolerance,
           p.portfolio_id, p.cash_balance, p.total_value,
           h.ticker, h.shares, h.average_buy_price
    FROM {SCHEMA}.clients c
    LEFT JOIN {SCHEMA}.portfolios p         ON p.client_id = c.client_id
    LEFT JOIN {SCHEMA}.portfolio_holdings h ON h.portfolio_id = p.portfolio_id
    WHERE c.client_id = :client_id
    ORDER BY p.portfolio_id, h.ticker
""")


def load_client_portfolio(db: DatabaseClient, client_id: int) -> dict[str, Any] | None:
    """Return the client's profile as a JSON-able dict, or None if no such client.

    Shape:
        {"client_name": str, "risk_tolerance": str | None,
         "portfolios": [{"cash_balance": float, "total_value": float,
                         "holdings": [{"ticker": str, "shares": int, "average_buy_price": float}]}]}
    """
    with db.session() as session:
        rows = session.execute(PROFILE_SQL, {"client_id": client_id}).mappings().all()
    if not rows:
        return None

    first = rows[0]
    portfolios: dict[int, dict[str, Any]] = {}
    for r in rows:
        pid = r["portfolio_id"]
        if pid is None:
            continue
        portfolio = portfolios.setdefault(
            pid,
            {
                "cash_balance": _num(r["cash_balance"]),
                "total_value": _num(r["total_value"]),
                "holdings": [],
            },
        )
        if r["ticker"] is not None:
            portfolio["holdings"].append(
                {
                    "ticker": r["ticker"],
                    "shares": r["shares"],
                    "average_buy_price": _num(r["average_buy_price"]),
                }
            )

    return {
        "client_name": f"{first['first_name']} {first['last_name']}".strip(),
        "risk_tolerance": first["risk_tolerance"],
        "portfolios": list(portfolios.values()),
    }


def _num(value: Any) -> Any:
    """DECIMAL columns come back as Decimal; JSON needs float."""
    return float(value) if isinstance(value, Decimal) else value
