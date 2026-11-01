"""Database access: one psycopg connection pool, SQL loaded from files with named parameters.

Sync psycopg is used on purpose: FastAPI runs sync handlers in a thread pool, and it works on the
Windows event loop as well as Linux. `prepare_threshold=None` keeps it compatible with Supabase's
transaction pooler (port 6543).
"""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from titlivo.settings import get_settings

QUERIES = Path(__file__).parent / "queries"
_pool: ConnectionPool | None = None


def pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            get_settings().database_url,
            min_size=1,
            max_size=10,
            kwargs={"row_factory": dict_row, "prepare_threshold": None, "autocommit": True},
            open=True,
        )
    return _pool


def close() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def tx() -> Iterator[Connection[dict[str, Any]]]:
    """One transaction: commits on success, rolls back on error."""
    with pool().connection() as conn, conn.transaction():
        yield conn


@lru_cache
def sql(name: str) -> str:
    return (QUERIES / f"{name}.sql").read_text(encoding="utf-8")


def fetch_all(name: str, params: dict[str, Any] | None = None, conn: Connection | None = None) -> list[dict[str, Any]]:
    if conn is not None:
        return conn.execute(sql(name), params or {}).fetchall()
    with pool().connection() as c:
        return c.execute(sql(name), params or {}).fetchall()


def fetch_one(name: str, params: dict[str, Any] | None = None, conn: Connection | None = None) -> dict[str, Any] | None:
    rows = fetch_all(name, params, conn)
    return rows[0] if rows else None
