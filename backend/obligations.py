from decimal import Decimal, InvalidOperation

from .db import transaction


ACTIVE_STATUSES = {"reserved", "ready"}
VALID_STATUSES = ACTIVE_STATUSES | {"paid", "cancelled"}


def _money(value) -> Decimal:
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("amount must be a decimal number") from exc
    if amount <= 0:
        raise ValueError("amount must be greater than 0")
    return amount


def _row(row) -> dict:
    return {
        "id": row["id"],
        "amount": row["amount"],
        "asset": row["asset"],
        "due_date": row["due_date"],
        "recipient": row["recipient"],
        "memo": row["memo"],
        "status": row["status"],
        "funding_plan_id": row["funding_plan_id"] if "funding_plan_id" in row.keys() else None,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_obligations(active_only: bool = False) -> list[dict]:
    select = """SELECT o.*,
        (SELECT opl.plan_id FROM obligation_plan_links opl
         WHERE opl.obligation_id=o.id ORDER BY opl.created_at DESC LIMIT 1) AS funding_plan_id
        FROM obligations o"""
    with transaction() as conn:
        if active_only:
            rows = conn.execute(
                select + " WHERE o.status IN ('reserved','ready') ORDER BY o.due_date IS NULL, o.due_date, o.id"
            ).fetchall()
        else:
            rows = conn.execute(select + " ORDER BY o.due_date IS NULL, o.due_date, o.id").fetchall()
    return [_row(row) for row in rows]


def get_obligation(obligation_id: int) -> dict | None:
    with transaction() as conn:
        row = conn.execute(
            """SELECT o.*,
               (SELECT opl.plan_id FROM obligation_plan_links opl
                WHERE opl.obligation_id=o.id ORDER BY opl.created_at DESC LIMIT 1) AS funding_plan_id
               FROM obligations o WHERE o.id=?""",
            (obligation_id,),
        ).fetchone()
    return _row(row) if row else None


def link_funding_plan(obligation_id: int, plan_id: str) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO obligation_plan_links(obligation_id, plan_id) VALUES (?, ?)",
            (obligation_id, plan_id),
        )


def create_obligation(amount, asset: str, due_date: str | None, recipient: str | None, memo: str) -> dict:
    value = _money(amount)
    normalized_asset = (asset or "USDC").upper()
    if normalized_asset != "USDC":
        raise ValueError("This release reserves USDC obligations only; other assets need a current valuation adapter")
    with transaction() as conn:
        cursor = conn.execute(
            """INSERT INTO obligations(amount, asset, due_date, recipient, memo)
               VALUES (?, ?, ?, ?, ?)""",
            (str(value), normalized_asset, due_date or None, recipient or None, memo or ""),
        )
        row = conn.execute("SELECT *, NULL AS funding_plan_id FROM obligations WHERE id=?", (cursor.lastrowid,)).fetchone()
    return _row(row)


def update_obligation_status(obligation_id: int, status: str) -> dict | None:
    if status not in VALID_STATUSES:
        raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
    with transaction() as conn:
        conn.execute(
            "UPDATE obligations SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, obligation_id),
        )
        row = conn.execute(
            """SELECT o.*,
               (SELECT opl.plan_id FROM obligation_plan_links opl
                WHERE opl.obligation_id=o.id ORDER BY opl.created_at DESC LIMIT 1) AS funding_plan_id
               FROM obligations o WHERE o.id=?""",
            (obligation_id,),
        ).fetchone()
    return _row(row) if row else None


def reserved_usdc(exclude_id: int | None = None) -> Decimal:
    total = Decimal("0")
    for item in list_obligations(active_only=True):
        if exclude_id is not None and item["id"] == exclude_id:
            continue
        if item["asset"] == "USDC":
            total += Decimal(item["amount"])
    return total


def get_asset_policies() -> dict[str, dict]:
    with transaction() as conn:
        rows = conn.execute("SELECT * FROM asset_policies ORDER BY asset").fetchall()
    return {
        row["asset"]: {"protected": bool(row["protected"]), "minimum_keep": row["minimum_keep"]}
        for row in rows
    }


def set_asset_policy(asset: str, protected: bool, minimum_keep=0) -> dict:
    normalized = (asset or "").upper().strip()
    if not normalized:
        raise ValueError("asset is required")
    minimum = Decimal(str(minimum_keep))
    if minimum < 0:
        raise ValueError("minimum_keep cannot be negative")
    with transaction() as conn:
        conn.execute(
            """INSERT INTO asset_policies(asset, protected, minimum_keep) VALUES (?, ?, ?)
               ON CONFLICT(asset) DO UPDATE SET protected=excluded.protected,
                 minimum_keep=excluded.minimum_keep, updated_at=CURRENT_TIMESTAMP""",
            (normalized, int(protected), str(minimum)),
        )
    return {"asset": normalized, "protected": protected, "minimum_keep": str(minimum)}
