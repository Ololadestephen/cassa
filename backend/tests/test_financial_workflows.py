import asyncio
import os
import tempfile
import unittest
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend import agent, mcp_client, pay, policy, sweep
from backend.main import app
from backend.obligations import create_obligation, get_obligation, list_obligations, set_asset_policy
from backend.services.affordability import assess_affordability
from backend.services.portfolio import build_portfolio
from backend.store import DEFAULT_ADDRESSBOOK, DEFAULT_CONFIG, get_paper, load, log_activity, save


class IsolatedDatabaseTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous_db = os.environ.get("CASSA_DB_PATH")
        self.previous_mock = os.environ.get("MOCK_MODE")
        os.environ["CASSA_DB_PATH"] = os.path.join(self.temp.name, "test.db")
        os.environ["MOCK_MODE"] = "true"
        save("config", dict(DEFAULT_CONFIG))
        save("addressbook", dict(DEFAULT_ADDRESSBOOK))
        save("activity", [])
        save("_seq", {"n": 0})
        save("paper", {"spot": {"USDC": 1000}, "earn": {}})

    def tearDown(self):
        if self.previous_db is None:
            os.environ.pop("CASSA_DB_PATH", None)
        else:
            os.environ["CASSA_DB_PATH"] = self.previous_db
        if self.previous_mock is None:
            os.environ.pop("MOCK_MODE", None)
        else:
            os.environ["MOCK_MODE"] = self.previous_mock
        self.temp.cleanup()


class StoreAndObligationTests(IsolatedDatabaseTest):
    def test_paper_reset_restores_reference_demo(self):
        client = TestClient(app)
        response = client.post("/api/paper/reset")
        self.assertEqual(response.status_code, 200, response.text)
        paper = get_paper()
        self.assertEqual(Decimal(str(paper["spot"]["USDC"])), Decimal("18"))
        self.assertEqual(Decimal(str(paper["earn"]["USDC"]["principal"])), Decimal("0"))
        self.assertGreaterEqual(len([asset for asset in paper["spot"] if asset != "USDC"]), 4)

        prices = {
            "source": "test",
            "fetched_at": 1,
            "BTCUSDC": {"price": "80000"},
            "DOGEUSDC": {"price": "0.09"},
            "ADAUSDC": {"price": "0.22"},
            "XRPUSDC": {"price": "1.40"},
            "TRXUSDC": {"price": "0.34"},
        }
        dust = asyncio.run(mcp_client.get_dust_convertible_assets("USDC", prices=prices))
        balances = {"mode": "paper", "source": "paper", "paper": paper, "prices": prices}
        with patch(
            "backend.services.portfolio.split_holdings",
            AsyncMock(return_value=(paper["spot"], 0, paper["earn"])),
        ), patch(
            "backend.services.portfolio.mcp_client.get_dust_convertible_assets",
            AsyncMock(return_value=dust),
        ):
            portfolio = asyncio.run(build_portfolio(balances=balances))
        assessment = asyncio.run(assess_affordability("25", minimum_reserve="5", portfolio=portfolio))
        self.assertEqual(assessment["shortfall_usdc"], "12.00")
        self.assertEqual(assessment["outcome"], "affordable_after_conversions")

    def test_activity_sequence_and_obligation_persist(self):
        first = log_activity({"type": "test", "ok": True})
        second = log_activity({"type": "test", "ok": True})
        self.assertEqual((first["ledger_entry_id"], second["ledger_entry_id"]), (1, 2))
        self.assertEqual([row["ledger_entry_id"] for row in load("activity", [])], [2, 1])
        created = create_obligation("25.00", "usdc", "2026-09-08", "alice", "Invoice")
        self.assertEqual(created["amount"], "25.00")
        self.assertEqual(list_obligations(active_only=True)[0]["id"], created["id"])


class AffordabilityTests(IsolatedDatabaseTest):
    def test_reference_shortfall_is_twelve(self):
        portfolio = {
            "free_usdc": "18",
            "unknown_assets": [],
            "holdings": [],
        }
        result = asyncio.run(assess_affordability("25", minimum_reserve="5", portfolio=portfolio))
        self.assertEqual(result["outcome"], "insufficient_eligible_funds")
        self.assertEqual(result["shortfall_usdc"], "12.00")
        self.assertEqual(result["projected_headroom_usdc"], "-12.00")

    def test_eligible_unprotected_balances_can_fund_shortfall(self):
        set_asset_policy("KEEP", True, 0)
        portfolio = {
            "free_usdc": "18",
            "unknown_assets": [],
            "holdings": [
                {"asset": "DUST", "dust_eligible": True, "protected": False, "recoverable_usdc": "12.25", "sellable_quantity": "40"},
                {"asset": "KEEP", "dust_eligible": False, "protected": True, "recoverable_usdc": None, "sellable_quantity": "3"},
            ],
        }
        result = asyncio.run(assess_affordability("25", minimum_reserve="5", portfolio=portfolio))
        self.assertEqual(result["outcome"], "affordable_after_conversions")
        self.assertEqual(result["selected_conversions"][0]["asset"], "DUST")
        self.assertEqual(result["projected_headroom_usdc"], "0.25")

    def test_selected_obligation_is_not_counted_twice(self):
        selected = create_obligation("25", "USDC", None, "alice", "Selected")
        create_obligation("7", "USDC", None, "bob", "Other")
        portfolio = {"free_usdc": "40", "unknown_assets": [], "holdings": []}
        result = asyncio.run(
            assess_affordability("25", minimum_reserve="5", obligation_id=selected["id"], portfolio=portfolio)
        )
        self.assertEqual(result["other_obligations_usdc"], "7.00")
        self.assertEqual(result["outcome"], "affordable_now")

    def test_portfolio_discovers_dynamic_small_balances_and_honors_protection(self):
        set_asset_policy("KEEP", True, 0)
        balances = {
            "mode": "paper",
            "source": "paper",
            "paper": {"spot": {"USDC": 18, "DUST": 10, "KEEP": 10}},
            "prices": {"DUSTUSDC": {"price": "0.30"}, "KEEPUSDC": {"price": "0.20"}},
        }
        dust = {
            "available": True,
            "source": "paper-fixture",
            "details": [
                {"asset": "DUST", "net_usdc": "2.94"},
                {"asset": "KEEP", "net_usdc": "1.96"},
            ],
        }
        with patch("backend.services.portfolio.split_holdings", AsyncMock(return_value=(balances["paper"]["spot"], 0, {}))), patch(
            "backend.services.portfolio.mcp_client.get_dust_convertible_assets", AsyncMock(return_value=dust)
        ):
            result = asyncio.run(build_portfolio(balances=balances))
        rows = {row["asset"]: row for row in result["holdings"]}
        self.assertTrue(rows["DUST"]["dust_eligible"])
        self.assertEqual(rows["DUST"]["recoverable_usdc"], "2.94")
        self.assertFalse(rows["KEEP"]["dust_eligible"])
        self.assertEqual(rows["KEEP"]["unavailable_reason"], "protected")


class PolicyAndConfirmationTests(IsolatedDatabaseTest):
    def test_non_usdc_payment_requires_valuation_and_obeys_cap(self):
        missing = policy.check_pay_policy("alice", "1", "BTC")
        blocked = policy.check_pay_policy("alice", "1", "BTC", amount_usdc="700")
        allowed = policy.check_pay_policy("alice", "0.001", "BTC", amount_usdc="80")
        self.assertFalse(missing["allowed"])
        self.assertFalse(blocked["allowed"])
        self.assertTrue(allowed["allowed"])
        self.assertTrue(allowed["needs_confirm"])

    def test_chat_never_supplies_live_confirmation(self):
        preview = {"ok": True, "needs_confirm": True, "to": {"id": "alice"}}
        with patch.object(agent, "preview_pay", AsyncMock(return_value=preview)), patch.object(
            agent, "execute_pay", AsyncMock()
        ) as execute:
            result = asyncio.run(agent._do_pay({"to": "alice", "amount": 250, "asset": "USDC"}, False))
        execute.assert_not_awaited()
        self.assertEqual(result["kind"], "confirm")

    def test_chat_sweep_is_always_a_preview(self):
        result = {
            "ok": True,
            "mode": "paper",
            "dca_fills": [],
            "earn": {"ok": True, "reason": "preview"},
        }
        with patch.object(agent, "run_sweep", AsyncMock(return_value=result)) as run:
            response = asyncio.run(agent._do_sweep({}, False))
        self.assertTrue(run.await_args.kwargs["dry_run"])
        self.assertIn("approve live execution", response["reply"])

    def test_every_live_payment_requires_confirmation(self):
        preview = {"ok": True, "needs_confirm": False, "to": {"email_or_uid": "alice"}}
        with patch.object(pay, "preview_pay", AsyncMock(return_value=preview)), patch.object(
            pay.mcp_client, "internal_transfer", AsyncMock()
        ) as transfer:
            result = asyncio.run(pay.execute_pay("alice", 10, "USDC", "", False, False, operation_id="confirm-required"))
        transfer.assert_not_awaited()
        self.assertTrue(result["needs_confirm"])

    def test_reserved_cash_blocks_payment_preview(self):
        create_obligation("940", "USDC", None, "bob", "Reserved")
        result = asyncio.run(pay.preview_pay("alice", 20, "USDC", ""))
        self.assertFalse(result["ok"])
        self.assertEqual(result["funding"]["spendable_usdc"], 10.0)

    def test_completed_operation_is_idempotent(self):
        preview = {"ok": True, "needs_confirm": False, "amount_usdc": 10, "to": {"email_or_uid": "alice"}}
        transfer = AsyncMock(return_value={"ok": True, "source": "paper"})
        with patch.object(pay, "preview_pay", AsyncMock(return_value=preview)), patch.object(
            pay.mcp_client, "internal_transfer", transfer
        ):
            first = asyncio.run(pay.execute_pay("alice", 10, "USDC", "memo", False, True, operation_id="same-operation"))
            second = asyncio.run(pay.execute_pay("alice", 10, "USDC", "memo", False, True, operation_id="same-operation"))
        self.assertTrue(first["ok"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(transfer.await_count, 1)

    def test_payment_terms_must_match_linked_obligation(self):
        obligation = create_obligation("25", "USDC", None, "alice", "Supplier")
        wrong_amount = asyncio.run(pay.preview_pay("alice", 24, "USDC", "", obligation["id"]))
        wrong_recipient = asyncio.run(pay.preview_pay("bob", 25, "USDC", "", obligation["id"]))
        self.assertFalse(wrong_amount["ok"])
        self.assertFalse(wrong_recipient["ok"])
        self.assertEqual(get_obligation(obligation["id"])["status"], "reserved")

    def test_matching_linked_payment_marks_obligation_paid_and_has_receipt(self):
        client = TestClient(app)
        obligation = create_obligation("25", "USDC", None, "alice", "Supplier")
        response = client.post(
            "/api/pay",
            json={
                "to": "alice",
                "amount": 25,
                "asset": "USDC",
                "memo": "Supplier",
                "obligation_id": obligation["id"],
                "dry_run": False,
                "confirmed": True,
                "operation_id": "linked-pay-001",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(get_obligation(obligation["id"])["status"], "paid")
        payment_receipts = [row for row in client.get("/api/receipts").json() if row["kind"] == "internal_payment"]
        self.assertEqual(len(payment_receipts), 1)
        self.assertEqual(payment_receipts[0]["obligation_id"], obligation["id"])


class SweepTests(IsolatedDatabaseTest):
    def _balances(self, usdc):
        return {
            "mode": "paper",
            "source": "paper",
            "paper": {"spot": {"USDC": usdc}},
            "prices": {
                "BTCUSDC": {"price": 100},
                "ETHUSDC": {"price": 100},
                "SOLUSDC": {"price": 100},
            },
        }

    def test_earn_uses_post_dca_balance(self):
        earn = AsyncMock(return_value={"ok": True, "source": "paper"})
        with patch.object(sweep.mcp_client, "get_balances", AsyncMock(side_effect=[self._balances(1000), self._balances(800)])), patch.object(
            sweep.mcp_client, "place_spot_order", AsyncMock(return_value={"ok": True, "source": "paper"})
        ), patch.object(sweep.mcp_client, "earn_subscribe", earn):
            result = asyncio.run(sweep.run_sweep(dry_run=False))
        self.assertEqual(earn.await_args.args[1], 750.0)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "completed")

    def test_partial_trade_failure_skips_earn_and_reports_partial(self):
        earn = AsyncMock()
        orders = AsyncMock(side_effect=[{"ok": True}, {"ok": False, "error": "failed"}, {"ok": True}])
        with patch.object(sweep.mcp_client, "get_balances", AsyncMock(side_effect=[self._balances(1000), self._balances(900)])), patch.object(
            sweep.mcp_client, "place_spot_order", orders
        ), patch.object(sweep.mcp_client, "earn_subscribe", earn):
            result = asyncio.run(sweep.run_sweep(dry_run=False))
        earn.assert_not_awaited()
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "partially_completed")
        self.assertEqual(result["earn"]["reason"], "skipped_after_dca_failure")


class FundingPlanTests(IsolatedDatabaseTest):
    def _prices(self):
        return {
            "source": "test",
            "fetched_at": 1,
            "DOGEUSDC": {"price": "0.20"},
            "ADAUSDC": {"price": "0.25"},
            "XRPUSDC": {"price": "0.25"},
        }

    def _create_plan(self, client):
        save("paper", {"spot": {"USDC": "18", "DOGE": "25", "ADA": "20", "XRP": "10"}, "earn": {}})
        return client.post(
            "/api/plans",
            json={"amount": 25, "minimum_reserve": 5, "recipient": "alice", "max_conversion_fee_pct": 2.5},
        )

    def test_approved_plan_recovers_multiple_small_balances_once(self):
        client = TestClient(app)
        with patch("backend.mcp_client.get_prices", AsyncMock(return_value=self._prices())):
            created = self._create_plan(client)
            self.assertEqual(created.status_code, 200, created.text)
            plan = created.json()
            self.assertEqual(plan["state"], "awaiting_approval")
            self.assertEqual(plan["assessment"]["outcome"], "affordable_after_conversions")
            self.assertEqual(len(plan["steps"]), 3)

            unapproved = client.post(
                f"/api/plans/{plan['id']}/execute",
                json={"version": plan["version"], "operation_id": "plan-op-0001"},
            )
            self.assertEqual(unapproved.status_code, 409)
            wrong_version = client.post(
                f"/api/plans/{plan['id']}/approve", json={"version": 99, "confirmed": True}
            )
            self.assertEqual(wrong_version.status_code, 409)

            approved = client.post(
                f"/api/plans/{plan['id']}/approve",
                json={"version": plan["version"], "confirmed": True},
            )
            self.assertEqual(approved.status_code, 200, approved.text)
            executed = client.post(
                f"/api/plans/{plan['id']}/execute",
                json={"version": plan["version"], "operation_id": "plan-op-0001"},
            )
            self.assertEqual(executed.status_code, 200, executed.text)
            result = executed.json()
            self.assertTrue(result["ok"])
            self.assertEqual(result["funding_status"], "funds_prepared")
            self.assertEqual(result["settlement_status"], "not_executed")
            self.assertEqual(len(result["conversion"]["receipts"]), 3)
            self.assertTrue(all(r["provider_id"].startswith("paper-dust-") for r in result["conversion"]["receipts"]))

            paper = get_paper()["spot"]
            self.assertEqual((paper["DOGE"], paper["ADA"], paper["XRP"]), ("0", "0", "0"))
            self.assertEqual(Decimal(paper["USDC"]), Decimal("30.25"))

            duplicate = client.post(
                f"/api/plans/{plan['id']}/execute",
                json={"version": plan["version"], "operation_id": "plan-op-0001"},
            )
            self.assertEqual(duplicate.status_code, 200)
            self.assertTrue(duplicate.json()["duplicate"])
            self.assertEqual(Decimal(get_paper()["spot"]["USDC"]), Decimal("30.25"))

    def test_asset_protected_after_approval_blocks_execution(self):
        client = TestClient(app)
        with patch("backend.mcp_client.get_prices", AsyncMock(return_value=self._prices())):
            plan = self._create_plan(client).json()
            client.post(
                f"/api/plans/{plan['id']}/approve",
                json={"version": plan["version"], "confirmed": True},
            )
            asset = plan["steps"][0]["input"]["asset"]
            set_asset_policy(asset, True, 0)
            response = client.post(
                f"/api/plans/{plan['id']}/execute",
                json={"version": plan["version"], "operation_id": "plan-op-0002"},
            )
            self.assertEqual(response.status_code, 409)
            self.assertIn("protected", response.json()["detail"])
            self.assertEqual(Decimal(get_paper()["spot"]["USDC"]), Decimal("18"))

    def test_fee_ceiling_blocks_plan_before_approval(self):
        client = TestClient(app)
        with patch("backend.mcp_client.get_prices", AsyncMock(return_value=self._prices())):
            save("paper", {"spot": {"USDC": "18", "DOGE": "25", "ADA": "20", "XRP": "10"}, "earn": {}})
            response = client.post(
                "/api/plans",
                json={"amount": 25, "minimum_reserve": 5, "recipient": "alice", "max_conversion_fee_pct": 0.5},
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["state"], "blocked")
        self.assertEqual(response.json()["assessment"]["outcome"], "blocked_by_conversion_cost")

    def test_expired_plan_cannot_be_approved(self):
        client = TestClient(app)
        with patch("backend.mcp_client.get_prices", AsyncMock(return_value=self._prices())):
            plan = self._create_plan(client).json()
        with patch("backend.plans.time.time", return_value=plan["expires_at"]):
            response = client.post(
                f"/api/plans/{plan['id']}/approve",
                json={"version": plan["version"], "confirmed": True},
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(client.get(f"/api/plans/{plan['id']}").json()["state"], "expired")

    def test_ambiguous_provider_error_requires_reconciliation(self):
        client = TestClient(app)
        with patch("backend.mcp_client.get_prices", AsyncMock(return_value=self._prices())):
            plan = self._create_plan(client).json()
        client.post(
            f"/api/plans/{plan['id']}/approve",
            json={"version": plan["version"], "confirmed": True},
        )
        with patch("backend.mcp_client.get_prices", AsyncMock(return_value=self._prices())), patch(
            "backend.plans.mcp_client.convert_dust_assets", AsyncMock(side_effect=TimeoutError("provider timeout"))
        ):
            response = client.post(
                f"/api/plans/{plan['id']}/execute",
                json={"version": plan["version"], "operation_id": "plan-op-0003"},
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["state"], "needs_reconciliation")
        retry = client.post(
            f"/api/plans/{plan['id']}/execute",
            json={"version": plan["version"], "operation_id": "plan-op-0003"},
        )
        self.assertEqual(retry.status_code, 409)
        self.assertIn("reconciliation", retry.json()["detail"])
        resolved = client.post(
            "/api/reconciliations/plan-op-0003/resolve-failed",
            json={"evidence": "Binance history checked: no conversion record", "confirmed": True},
        )
        self.assertEqual(resolved.status_code, 200, resolved.text)
        self.assertEqual(resolved.json()["state"], "failed")
        self.assertEqual(client.get(f"/api/plans/{plan['id']}").json()["state"], "failed")
        self.assertEqual(client.get("/api/reconciliations").json(), [])

    def test_linked_obligation_becomes_ready_and_receipts_export(self):
        client = TestClient(app)
        obligation = create_obligation("25", "USDC", "2026-09-08", "alice", "Supplier")
        save("paper", {"spot": {"USDC": "18", "DOGE": "25", "ADA": "20", "XRP": "10"}, "earn": {}})
        with patch("backend.mcp_client.get_prices", AsyncMock(return_value=self._prices())):
            created = client.post(
                "/api/plans",
                json={"amount": 25, "minimum_reserve": 5, "obligation_id": obligation["id"]},
            )
            self.assertEqual(created.status_code, 200, created.text)
            plan = created.json()
            self.assertEqual(plan["request"]["recipient"], "alice")
            self.assertEqual(get_obligation(obligation["id"])["funding_plan_id"], plan["id"])
            client.post(
                f"/api/plans/{plan['id']}/approve",
                json={"version": plan["version"], "confirmed": True},
            )
            executed = client.post(
                f"/api/plans/{plan['id']}/execute",
                json={"version": plan["version"], "operation_id": "linked-plan-001"},
            )
        self.assertTrue(executed.json()["ok"])
        self.assertEqual(get_obligation(obligation["id"])["status"], "ready")
        receipts = client.get("/api/receipts").json()
        self.assertEqual(len(receipts), 3)
        self.assertTrue(all(row["obligation_id"] == obligation["id"] for row in receipts))
        exported = client.get("/api/receipts/export.csv")
        self.assertEqual(exported.status_code, 200)
        self.assertIn("provider_id", exported.text)
        self.assertIn(plan["id"], exported.text)

    def test_linked_obligation_terms_must_match(self):
        client = TestClient(app)
        obligation = create_obligation("25", "USDC", None, "alice", "Supplier")
        response = client.post(
            "/api/plans",
            json={"amount": 24, "minimum_reserve": 5, "obligation_id": obligation["id"]},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("must match", response.json()["detail"])

    def test_competing_approved_plans_cannot_reserve_same_assets(self):
        client = TestClient(app)
        with patch("backend.mcp_client.get_prices", AsyncMock(return_value=self._prices())):
            first = self._create_plan(client).json()
            second = client.post(
                "/api/plans",
                json={"amount": 25, "minimum_reserve": 5, "recipient": "alice"},
            ).json()
        accepted = client.post(
            f"/api/plans/{first['id']}/approve",
            json={"version": first["version"], "confirmed": True},
        )
        conflict = client.post(
            f"/api/plans/{second['id']}/approve",
            json={"version": second["version"], "confirmed": True},
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(conflict.status_code, 409)
        self.assertIn("reserved", conflict.json()["detail"])

    def test_changed_quantity_expires_plan_before_conversion(self):
        client = TestClient(app)
        with patch("backend.mcp_client.get_prices", AsyncMock(return_value=self._prices())):
            plan = self._create_plan(client).json()
        client.post(
            f"/api/plans/{plan['id']}/approve",
            json={"version": plan["version"], "confirmed": True},
        )
        paper = get_paper()
        paper["spot"]["DOGE"] = "24"
        save("paper", paper)
        convert = AsyncMock()
        with patch("backend.mcp_client.get_prices", AsyncMock(return_value=self._prices())), patch(
            "backend.plans.mcp_client.convert_dust_assets", convert
        ):
            response = client.post(
                f"/api/plans/{plan['id']}/execute",
                json={"version": plan["version"], "operation_id": "changed-plan-01"},
            )
        self.assertEqual(response.status_code, 409)
        self.assertIn("balance changed", response.json()["detail"])
        convert.assert_not_awaited()
        self.assertEqual(client.get(f"/api/plans/{plan['id']}").json()["state"], "expired")

    def test_receipts_survive_post_conversion_fee_violation(self):
        client = TestClient(app)
        with patch("backend.mcp_client.get_prices", AsyncMock(return_value=self._prices())):
            plan = self._create_plan(client).json()
        client.post(
            f"/api/plans/{plan['id']}/approve",
            json={"version": plan["version"], "confirmed": True},
        )
        receipts = []
        for step in plan["steps"]:
            gross = Decimal(step["input"]["gross_usdc"])
            receipts.append({
                "provider_id": f"provider-{step['ordinal']}",
                "from_asset": step["input"]["asset"],
                "amount": step["input"]["quantity"],
                "gross_usdc": str(gross),
                "service_charge_usdc": str(gross * Decimal("0.03")),
                "net_usdc": str(gross * Decimal("0.97")),
            })
        conversion = {"ok": True, "source": "paper", "receipts": receipts, "net_received": "12.125"}
        with patch("backend.mcp_client.get_prices", AsyncMock(return_value=self._prices())), patch(
            "backend.plans.mcp_client.convert_dust_assets", AsyncMock(return_value=conversion)
        ):
            response = client.post(
                f"/api/plans/{plan['id']}/execute",
                json={"version": plan["version"], "operation_id": "fee-change-001"},
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["state"], "partially_completed")
        stored = client.get(f"/api/plans/{plan['id']}").json()
        self.assertTrue(all(step["provider_id"] for step in stored["steps"]))


class ApiConfirmationTests(IsolatedDatabaseTest):
    def test_write_endpoints_reject_missing_confirmation(self):
        client = TestClient(app)
        sweep_response = client.post(
            "/api/sweep",
            json={"dca_total_usdc": 200, "dca_split": {"BTC": 1}, "dry_run": False},
        )
        earn_response = client.post(
            "/api/earn/redeem", json={"asset": "USDC", "amount": 1, "dry_run": False}
        )
        pay_response = client.post(
            "/api/pay", json={"to": "alice", "amount": 10, "asset": "USDC", "dry_run": False}
        )
        self.assertEqual(sweep_response.status_code, 409)
        self.assertEqual(earn_response.status_code, 409)
        self.assertTrue(pay_response.json()["needs_confirm"])


if __name__ == "__main__":
    unittest.main()
