import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


DEFAULT_DB_PATH = Path(__file__).parent / "data" / "cassa.db"


def db_path() -> Path:
    configured = os.getenv("CASSA_DB_PATH")
    return Path(configured) if configured else DEFAULT_DB_PATH


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS kv_store (
            name TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS obligations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount TEXT NOT NULL,
            asset TEXT NOT NULL,
            due_date TEXT,
            recipient TEXT,
            memo TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'reserved',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS asset_policies (
            asset TEXT PRIMARY KEY,
            protected INTEGER NOT NULL DEFAULT 0,
            minimum_keep TEXT NOT NULL DEFAULT '0',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS execution_records (
            operation_id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            state TEXT NOT NULL,
            request_json TEXT NOT NULL,
            result_json TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS funding_plans (
            id TEXT PRIMARY KEY,
            version INTEGER NOT NULL,
            state TEXT NOT NULL,
            request_json TEXT NOT NULL,
            assessment_json TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            approval_json TEXT,
            result_json TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS plan_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id TEXT NOT NULL REFERENCES funding_plans(id),
            ordinal INTEGER NOT NULL,
            kind TEXT NOT NULL,
            state TEXT NOT NULL,
            input_json TEXT NOT NULL,
            result_json TEXT,
            provider_id TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(plan_id, ordinal)
        );
        CREATE TABLE IF NOT EXISTS obligation_plan_links (
            obligation_id INTEGER NOT NULL REFERENCES obligations(id),
            plan_id TEXT NOT NULL REFERENCES funding_plans(id),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(obligation_id, plan_id)
        );
        CREATE TABLE IF NOT EXISTS plan_asset_locks (
            asset TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL REFERENCES funding_plans(id),
            expires_at INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS reconciliation_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id TEXT NOT NULL REFERENCES execution_records(operation_id),
            resolution TEXT NOT NULL,
            evidence TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    return conn


@contextmanager
def transaction():
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def encode(value) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def decode(value: str):
    return json.loads(value)
