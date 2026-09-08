import csv
import io
import json

from .db import transaction


def _provider_id(payload: dict, fallback: str) -> str:
    for key in ("tranId", "transactionId", "orderId", "id"):
        value = payload.get(key)
        if value is not None:
            return str(value)
    return fallback


def list_receipts(limit: int = 100) -> list[dict]:
    receipts: list[dict] = []
    with transaction() as conn:
        conversions = conn.execute(
            """SELECT ps.plan_id, ps.ordinal, ps.state, ps.result_json, ps.provider_id,
                      ps.updated_at, opl.obligation_id
               FROM plan_steps ps
               LEFT JOIN obligation_plan_links opl ON opl.plan_id=ps.plan_id
               WHERE ps.provider_id IS NOT NULL
               ORDER BY ps.updated_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        payments = conn.execute(
            """SELECT operation_id, state, request_json, result_json, updated_at
               FROM execution_records
               WHERE kind='pay' AND state='completed' AND result_json IS NOT NULL
               ORDER BY updated_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    for row in conversions:
        result = json.loads(row["result_json"])
        receipts.append(
            {
                "receipt_id": f"conversion:{row['plan_id']}:{row['ordinal']}",
                "kind": "small_balance_conversion",
                "state": row["state"],
                "provider_id": row["provider_id"],
                "plan_id": row["plan_id"],
                "obligation_id": row["obligation_id"],
                "from_asset": result.get("from_asset"),
                "from_amount": result.get("amount"),
                "to_asset": "USDC",
                "gross_usdc": result.get("gross_usdc"),
                "fee_usdc": result.get("service_charge_usdc"),
                "net_usdc": result.get("net_usdc"),
                "recipient": None,
                "recorded_at": row["updated_at"],
            }
        )
    for row in payments:
        request = json.loads(row["request_json"])
        result = json.loads(row["result_json"])
        payment = result.get("payment") or {}
        receipts.append(
            {
                "receipt_id": f"payment:{row['operation_id']}",
                "kind": "internal_payment",
                "state": row["state"],
                "provider_id": _provider_id(payment, row["operation_id"]),
                "plan_id": None,
                "obligation_id": request.get("obligation_id"),
                "from_asset": request.get("asset"),
                "from_amount": request.get("amount"),
                "to_asset": request.get("asset"),
                "gross_usdc": result.get("preview", {}).get("amount_usdc"),
                "fee_usdc": None,
                "net_usdc": result.get("preview", {}).get("amount_usdc"),
                "recipient": request.get("to"),
                "recorded_at": row["updated_at"],
            }
        )
    receipts.sort(key=lambda item: item["recorded_at"] or "", reverse=True)
    return receipts[:limit]


def receipts_csv(limit: int = 1000) -> str:
    rows = list_receipts(limit)
    fields = [
        "receipt_id",
        "kind",
        "state",
        "provider_id",
        "plan_id",
        "obligation_id",
        "from_asset",
        "from_amount",
        "to_asset",
        "gross_usdc",
        "fee_usdc",
        "net_usdc",
        "recipient",
        "recorded_at",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
