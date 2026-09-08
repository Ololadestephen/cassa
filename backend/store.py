"""Transactional local state for Cassa.

Legacy JSON is imported lazily into SQLite on first access and left untouched as
an audit-friendly backup. CASSA_PROVIDER selects the provider boundary; the
older MOCK_MODE flag remains a backwards-compatible paper/REST default.
"""
import json
import os
import time
from pathlib import Path

from .db import decode, encode, transaction

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def _path(name: str) -> Path:
    return DATA_DIR / f"{name}.json"


def load(name: str, default):
    with transaction() as conn:
        row = conn.execute("SELECT payload FROM kv_store WHERE name = ?", (name,)).fetchone()
        if row is not None:
            try:
                return decode(row["payload"])
            except Exception:
                return default
        value = default
        legacy = _path(name)
        if legacy.exists():
            try:
                value = json.loads(legacy.read_text())
            except Exception:
                value = default
        conn.execute("INSERT INTO kv_store(name, payload) VALUES (?, ?)", (name, encode(value)))
        return value


def save(name: str, obj) -> None:
    with transaction() as conn:
        conn.execute(
            """INSERT INTO kv_store(name, payload) VALUES (?, ?)
               ON CONFLICT(name) DO UPDATE SET payload=excluded.payload, updated_at=CURRENT_TIMESTAMP""",
            (name, encode(obj)),
        )


def provider_mode() -> str:
    explicit = os.getenv("CASSA_PROVIDER", "").strip().lower()
    aliases = {
        "paper": "paper",
        "agent-os": "agent-os-readonly",
        "agent-os-readonly": "agent-os-readonly",
        "binance-rest": "binance-rest",
        "live-exchange": "binance-rest",
    }
    if explicit:
        return aliases.get(explicit, "invalid")
    return "paper" if os.getenv("MOCK_MODE", "true").lower() == "true" else "binance-rest"


def is_mock() -> bool:
    return provider_mode() == "paper"


def is_agent_os_readonly() -> bool:
    return provider_mode() == "agent-os-readonly"


def is_binance_rest() -> bool:
    return provider_mode() == "binance-rest"


DEFAULT_CONFIG = {
    "max_per_pay_usdc": 500,
    "max_daily_usdc": 2000,
    "require_confirm_over_usdc": 200,
    "max_x402_per_day_usdc": 20,
    "dca_total_usdc": 200,
    "dca_split": {"BTC": 0.5, "ETH": 0.3, "SOL": 0.2},
    "sweep_idle_over_usdc": 100,
    "dust_under_usdc": 5,
    "minimum_reserve_usdc": 50,
}

DEFAULT_ADDRESSBOOK = {
    "alice": {
        "label": "Alice — VA",
        "asset": "USDC",
        "email_or_uid": "alice.va@example.org",
        "rail": "internal-transfer",
    },
    "bob": {
        "label": "Bob — Designer",
        "asset": "USDC",
        "email_or_uid": "bob.designer@example.org",
        "rail": "internal-transfer",
    },
}

PAPER_DEFAULT = {
    "spot": {"USDC": 18.0, "BTC": 0.002, "DOGE": 35.0, "ADA": 15.0, "XRP": 3.0, "TRX": 12.0},
    "earn": {"USDC": {"principal": 0.0, "accrued_total": 0.0, "apr_pct": 4.2, "updated_at": 0}},
}

PAPER_APR_PCT = 4.2


def get_earn_ledger(paper: dict) -> dict:
    earn = paper.get("earn")
    if not isinstance(earn, dict):
        earn = {}
        paper["earn"] = earn
    if "USDC" not in earn:
        earn["USDC"] = {"principal": 250.0, "accrued_total": 0.0, "apr_pct": PAPER_APR_PCT, "updated_at": int(time.time())}
    return earn


def get_config() -> dict:
    cfg = load("config", dict(DEFAULT_CONFIG))
    for key, value in DEFAULT_CONFIG.items():
        cfg.setdefault(key, value)
    try:
        cfg["max_per_pay_usdc"] = min(float(os.getenv("CASSA_MAX_PER_PAY_USDC", cfg["max_per_pay_usdc"])), 500.0)
    except ValueError:
        cfg["max_per_pay_usdc"] = 500.0
    try:
        cfg["max_daily_usdc"] = float(os.getenv("CASSA_MAX_DAILY_USDC", cfg["max_daily_usdc"]))
    except ValueError:
        cfg["max_daily_usdc"] = 2000.0
    try:
        cfg["require_confirm_over_usdc"] = float(
            os.getenv("CASSA_REQUIRE_CONFIRM_OVER_USDC", cfg["require_confirm_over_usdc"])
        )
    except ValueError:
        cfg["require_confirm_over_usdc"] = 200.0
    try:
        cfg["minimum_reserve_usdc"] = float(
            os.getenv("CASSA_MINIMUM_RESERVE_USDC", cfg["minimum_reserve_usdc"])
        )
    except ValueError:
        cfg["minimum_reserve_usdc"] = 50.0
    cfg["max_x402_per_day_usdc"] = 20.0
    return cfg


def get_addressbook() -> dict:
    book = load("addressbook", dict(DEFAULT_ADDRESSBOOK))
    if not book:
        book = dict(DEFAULT_ADDRESSBOOK)
        save("addressbook", book)
    return book


def get_paper() -> dict:
    paper = load("paper", {"spot": dict(PAPER_DEFAULT["spot"])})
    if not isinstance(paper, dict) or "spot" not in paper:
        paper = {"spot": dict(PAPER_DEFAULT["spot"])}
        save("paper", paper)
    return paper


def next_ledger_id() -> int:
    with transaction() as conn:
        row = conn.execute("SELECT payload FROM kv_store WHERE name='_seq'").fetchone()
        try:
            n = int(decode(row["payload"]).get("n", 0)) + 1 if row else 1
        except (ValueError, TypeError, AttributeError):
            n = 1
        conn.execute(
            """INSERT INTO kv_store(name, payload) VALUES ('_seq', ?)
               ON CONFLICT(name) DO UPDATE SET payload=excluded.payload, updated_at=CURRENT_TIMESTAMP""",
            (encode({"n": n}),),
        )
        return n


def log_activity(entry: dict) -> dict:
    with transaction() as conn:
        log_row = conn.execute("SELECT payload FROM kv_store WHERE name='activity'").fetchone()
        seq_row = conn.execute("SELECT payload FROM kv_store WHERE name='_seq'").fetchone()
        if log_row:
            try:
                log = decode(log_row["payload"])
            except Exception:
                log = []
        else:
            try:
                log = json.loads(_path("activity").read_text()) if _path("activity").exists() else []
            except Exception:
                log = []
        try:
            n = int(decode(seq_row["payload"]).get("n", 0)) + 1 if seq_row else 1
        except (ValueError, TypeError, AttributeError):
            n = 1
        record = {**entry, "ledger_entry_id": n, "recorded_at": int(time.time())}
        log.insert(0, record)
        for name, value in (("_seq", {"n": n}), ("activity", log[:200])):
            conn.execute(
                """INSERT INTO kv_store(name, payload) VALUES (?, ?)
                   ON CONFLICT(name) DO UPDATE SET payload=excluded.payload, updated_at=CURRENT_TIMESTAMP""",
                (name, encode(value)),
            )
        return record
