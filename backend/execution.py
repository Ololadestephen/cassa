import json

from .db import transaction


def get_execution(operation_id: str) -> dict | None:
    with transaction() as conn:
        row = conn.execute("SELECT * FROM execution_records WHERE operation_id=?", (operation_id,)).fetchone()
    if row is None:
        return None
    return {
        "operation_id": row["operation_id"],
        "kind": row["kind"],
        "state": row["state"],
        "request": json.loads(row["request_json"]),
        "result": json.loads(row["result_json"]) if row["result_json"] else None,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_executions(state: str | None = None, limit: int = 100) -> list[dict]:
    with transaction() as conn:
        if state:
            rows = conn.execute(
                "SELECT operation_id FROM execution_records WHERE state=? ORDER BY updated_at DESC LIMIT ?",
                (state, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT operation_id FROM execution_records ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [get_execution(row["operation_id"]) for row in rows]


def resolve_failed_execution(operation_id: str, evidence: str, confirmed: bool) -> dict:
    if not confirmed:
        raise ValueError("Reconciliation requires confirmed=true")
    evidence = (evidence or "").strip()
    if len(evidence) < 8:
        raise ValueError("Record the provider-history evidence used to confirm failure")
    with transaction() as conn:
        row = conn.execute(
            "SELECT * FROM execution_records WHERE operation_id=?", (operation_id,)
        ).fetchone()
        if row is None:
            raise LookupError("Execution not found")
        if row["state"] != "needs_reconciliation":
            raise ValueError(f"Execution is {row['state']}, not needs_reconciliation")
        request = json.loads(row["request_json"])
        previous = json.loads(row["result_json"]) if row["result_json"] else {}
        result = {
            **previous,
            "ok": False,
            "state": "failed",
            "reconciliation": {
                "resolution": "provider_confirmed_failed",
                "evidence": evidence,
            },
        }
        conn.execute(
            "UPDATE execution_records SET state='failed', result_json=?, updated_at=CURRENT_TIMESTAMP WHERE operation_id=?",
            (json.dumps(result, sort_keys=True, separators=(",", ":")), operation_id),
        )
        conn.execute(
            "INSERT INTO reconciliation_events(operation_id, resolution, evidence) VALUES (?, 'provider_confirmed_failed', ?)",
            (operation_id, evidence),
        )
        if row["kind"] == "funding_plan" and request.get("plan_id"):
            conn.execute(
                "UPDATE funding_plans SET state='failed', result_json=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (json.dumps(result, sort_keys=True), request["plan_id"]),
            )
            conn.execute("DELETE FROM plan_asset_locks WHERE plan_id=?", (request["plan_id"],))
    return get_execution(operation_id)


def begin_execution(operation_id: str, kind: str, request: dict) -> tuple[bool, dict]:
    with transaction() as conn:
        existing = conn.execute("SELECT * FROM execution_records WHERE operation_id=?", (operation_id,)).fetchone()
        if existing is None:
            conn.execute(
                "INSERT INTO execution_records(operation_id, kind, state, request_json) VALUES (?, ?, 'executing', ?)",
                (operation_id, kind, json.dumps(request, sort_keys=True, separators=(",", ":"))),
            )
            return True, {"operation_id": operation_id, "kind": kind, "state": "executing", "request": request}
    return False, get_execution(operation_id)


def claim_plan_execution(operation_id: str, plan_id: str, version: int, request: dict) -> tuple[bool, dict]:
    """Atomically claim one approved plan and create its execution record."""
    with transaction() as conn:
        existing = conn.execute(
            "SELECT * FROM execution_records WHERE operation_id=?", (operation_id,)
        ).fetchone()
        if existing is not None:
            return False, {
                "operation_id": existing["operation_id"],
                "kind": existing["kind"],
                "state": existing["state"],
                "request": json.loads(existing["request_json"]),
                "result": json.loads(existing["result_json"]) if existing["result_json"] else None,
            }
        plan = conn.execute(
            "SELECT version, state FROM funding_plans WHERE id=?", (plan_id,)
        ).fetchone()
        if plan is None:
            raise LookupError("Funding plan not found")
        if plan["version"] != version:
            raise ValueError("Plan version changed; review the current plan")
        if plan["state"] != "approved":
            raise ValueError(f"Plan must be approved before execution; current state is {plan['state']}")
        conn.execute(
            "INSERT INTO execution_records(operation_id, kind, state, request_json) VALUES (?, 'funding_plan', 'executing', ?)",
            (operation_id, json.dumps(request, sort_keys=True, separators=(",", ":"))),
        )
        updated = conn.execute(
            "UPDATE funding_plans SET state='executing', updated_at=CURRENT_TIMESTAMP WHERE id=? AND version=? AND state='approved'",
            (plan_id, version),
        )
        if updated.rowcount != 1:
            raise ValueError("Funding plan was claimed by another execution")
    return True, {"operation_id": operation_id, "kind": "funding_plan", "state": "executing", "request": request}


def finish_execution(operation_id: str, state: str, result: dict) -> dict:
    with transaction() as conn:
        conn.execute(
            """UPDATE execution_records SET state=?, result_json=?, updated_at=CURRENT_TIMESTAMP
               WHERE operation_id=?""",
            (state, json.dumps(result, sort_keys=True, separators=(",", ":")), operation_id),
        )
    return get_execution(operation_id)
