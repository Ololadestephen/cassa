"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, timeAgo } from "../../lib/api";

type ChatMsg = { role: "you" | "cassa"; text: string; kind?: string; at?: number; via?: string };

function fmt(n: unknown, d = 2) {
  const x = Number(n);
  if (!isFinite(x)) return "—";
  return x.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
}

export default function Desk() {
  const [online, setOnline] = useState<boolean | null>(null);
  const [health, setHealth] = useState<any>(null);
  const [markets, setMarkets] = useState<any[]>([]);
  const [bal, setBal] = useState<any>(null);
  const [portfolio, setPortfolio] = useState<any>(null);
  const [digest, setDigest] = useState<any>(null);
  const [activity, setActivity] = useState<any[]>([]);
  const [book, setBook] = useState<Record<string, any>>({});
  const [obligations, setObligations] = useState<any[]>([]);
  const [capabilities, setCapabilities] = useState<any>(null);
  const [msgs, setMsgs] = useState<ChatMsg[]>([
    { role: "cassa", text: "Check what you can afford, protect holdings, prepare payment funds, and review every action before execution." },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [dryRun, setDryRun] = useState(true);
  const [dcaTotal, setDcaTotal] = useState("200");
  const [splitBtc, setSplitBtc] = useState("50");
  const [splitEth, setSplitEth] = useState("30");
  const [splitSol, setSplitSol] = useState("20");
  const [sweepResult, setSweepResult] = useState<any>(null);
  const [sweepError, setSweepError] = useState<string>("");
  const [payTo, setPayTo] = useState("alice");
  const [payAmt, setPayAmt] = useState("250");
  const [payMemo, setPayMemo] = useState("September VA");
  const [payObligationId, setPayObligationId] = useState<number | undefined>();
  const [payPreview, setPayPreview] = useState<any>(null);
  const [payError, setPayError] = useState<string>("");
  const [showConfirm, setShowConfirm] = useState(false);
  const [newId, setNewId] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [newDest, setNewDest] = useState("");
  const [bookError, setBookError] = useState<string>("");
  const [redeemAmt, setRedeemAmt] = useState("50");
  const [redeemResult, setRedeemResult] = useState<any>(null);
  const [affordAmount, setAffordAmount] = useState("25");
  const [affordReserve, setAffordReserve] = useState("5");
  const [affordRecipient, setAffordRecipient] = useState("alice");
  const [affordResult, setAffordResult] = useState<any>(null);
  const [affordObligationId, setAffordObligationId] = useState<number | undefined>();
  const [affordError, setAffordError] = useState("");
  const [fundingPlan, setFundingPlan] = useState<any>(null);
  const [fundingPlans, setFundingPlans] = useState<any[]>([]);
  const [planError, setPlanError] = useState("");
  const [obligationMemo, setObligationMemo] = useState("Supplier invoice");
  const [chatOpen, setChatOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const last = msgs[msgs.length - 1];
    if (!chatOpen && last && last.role === "cassa" && last.at) setUnread((u) => u + 1);
  }, [msgs, chatOpen]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [msgs, busy]);

  const refresh = useCallback(async () => {
    try {
      const [h, mk, b, pf, dg, ac, cf, ob, cp, pl] = await Promise.all([
        api.health(), api.market(), api.balance(), api.portfolio(), api.digest(), api.activity(), api.config(), api.obligations(), api.capabilities(), api.plans(),
      ]);
      setHealth(h); setMarkets(mk.markets); setBal(b); setPortfolio(pf);
      setDigest(dg); setActivity(ac); setBook(cf.addressbook); setObligations(ob); setCapabilities(cp); setFundingPlans(pl);
      setOnline(true);
    } catch {
      setOnline(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 15000);
    return () => clearInterval(timer);
  }, [refresh]);

  async function send(text: string) {
    const clean = text.trim();
    if (!clean || busy) return;
    setMsgs((m) => [...m, { role: "you", text: clean, at: Date.now() }]);
    setInput("");
    setBusy(true);
    try {
      const r = await api.chat(clean, dryRun);
      setMsgs((m) => [...m, { role: "cassa", text: r.reply, kind: r.kind, at: Date.now(), via: r.parsed_by }]);
      if (r.kind === "sweep" && r.data?.ok) setSweepResult(r.data);
      if (r.kind === "pay") setPayPreview(r.data);
    } catch (e: any) {
      setMsgs((m) => [...m, { role: "cassa", text: `Backend offline: ${String(e.message).slice(0, 160)}` }]);
    }
    setBusy(false);
    refresh();
  }

  async function runSweep() {
    setBusy(true);
    setSweepError("");
    try {
      const confirmed = dryRun || window.confirm(`Execute this investment allocation?\n\nDCA: $${dcaTotal}\nBTC ${splitBtc}% · ETH ${splitEth}% · SOL ${splitSol}%\nSurplus above the reserve may move to Earn.`);
      if (!confirmed) { setBusy(false); return; }
      const operationId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `sweep-${Date.now()}`;
      const r = await api.sweep({
        dca_total_usdc: parseFloat(dcaTotal) || 0,
        dca_split: { BTC: (parseFloat(splitBtc) || 0) / 100, ETH: (parseFloat(splitEth) || 0) / 100, SOL: (parseFloat(splitSol) || 0) / 100 },
        sweep_idle_over_usdc: 100,
        dust_under_usdc: 5,
        dry_run: dryRun,
        confirmed: !dryRun,
        operation_id: operationId,
      });
      setSweepResult(r);
      const fills = r.dca_fills.map((f: any) => `${f.asset} $${fmt(f.quote_usdc, 0)} @ $${fmt(f.price)}`).join(" · ");
      setMsgs((m) => [...m, { role: "cassa", text: `Sweep ${dryRun ? "preview" : "executed"} [${r.mode}]: ${fills}.`, at: Date.now() }]);
    } catch (e: any) {
      let reason = e.message;
      try { reason = JSON.parse(e.message)?.detail ?? e.message; } catch {}
      setSweepError(String(reason).slice(0, 300));
    }
    setBusy(false);
    refresh();
  }

  async function previewPay() {
    setBusy(true);
    setPayError("");
    setPayPreview(null);
    try {
      const r = await api.pay(payTo, parseFloat(payAmt) || 0, "USDC", payMemo, true, false, undefined, payObligationId);
      setPayPreview(r);
      setMsgs((m) => [...m, {
        role: "cassa",
        text: r.ok ? `Preview: ${r.amount} USDC → @${payTo} over internal transfer. Confirm needed: ${r.needs_confirm}.` : `Blocked: ${r.error}`,
        at: Date.now(),
      }]);
    } catch (e: any) {
      setPayError(String(e.message).slice(0, 300));
    }
    setBusy(false);
  }

  async function confirmPay() {
    if (!payPreview?.ok) return;
    setBusy(true);
    setPayError("");
    try {
      const operationId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `pay-${Date.now()}`;
      const r = await api.pay(payTo, parseFloat(payAmt) || 0, "USDC", payMemo, dryRun, true, operationId, payObligationId);
      setPayPreview(r);
      setShowConfirm(false);
      setMsgs((m) => [...m, {
        role: "cassa",
        text: r.ok
          ? dryRun ? `Dry-run confirmed for ${payAmt} USDC → @${payTo} (no funds moved).` : `Sent ${payAmt} USDC → @${payTo}. Ledger entry ${r.ledger_entry_id}.`
          : `Send failed: ${r.error ?? r.message}`,
        at: Date.now(),
      }]);
    } catch (e: any) {
      setPayError(String(e.message).slice(0, 300));
    }
    setBusy(false);
    refresh();
  }

  async function redeemEarn() {
    setBusy(true);
    try {
      const confirmed = dryRun || window.confirm(`Redeem ${redeemAmt} USDC from Flexible Earn?`);
      if (!confirmed) { setBusy(false); return; }
      const r = await api.earnRedeem(parseFloat(redeemAmt) || 0, dryRun, !dryRun);
      setRedeemResult(r);
      setMsgs((m) => [...m, { role: "cassa", text: r.ok ? `Redeem ${dryRun ? "preview" : "executed"}: ${redeemAmt} USDC from Flexible Earn (${r.source}).` : `Redeem blocked: ${r.error}`, at: Date.now() }]);
    } catch (e: any) {
      setRedeemResult({ ok: false, error: String(e.message).slice(0, 200) });
    }
    setBusy(false);
    refresh();
  }

  async function addRecipient() {
    setBookError("");
    try {
      const r = await api.addRecipient(newId, newLabel, newDest || newId);
      setBook(r.addressbook);
      setNewId(""); setNewLabel(""); setNewDest("");
      refresh();
    } catch (e: any) {
      let reason = e.message;
      try { reason = JSON.parse(e.message)?.detail ?? e.message; } catch {}
      setBookError(String(reason).slice(0, 300));
    }
  }

  async function checkAffordability() {
    setBusy(true); setAffordError("");
    try {
      const result = await api.affordability({
        amount: parseFloat(affordAmount) || 0,
        minimum_reserve: parseFloat(affordReserve) || 0,
        recipient: affordRecipient || undefined,
        obligation_id: affordObligationId,
      });
      setAffordResult(result);
      setFundingPlan(null);
      setPlanError("");
    } catch (e: any) {
      setAffordError(String(e.message).slice(0, 300));
    }
    setBusy(false);
  }

  async function createFundingPlan() {
    setBusy(true); setPlanError("");
    try {
      const plan = await api.createPlan({
        amount: parseFloat(affordAmount) || 0,
        minimum_reserve: parseFloat(affordReserve) || 0,
        recipient: affordRecipient || undefined,
        obligation_id: affordObligationId,
        max_conversion_fee_pct: 2.5,
        max_slippage_pct: 1,
        validity_seconds: 600,
      });
      setFundingPlan(plan);
      setFundingPlans((plans) => [plan, ...plans.filter((item) => item.id !== plan.id)]);
    } catch (e: any) {
      let reason = e.message;
      try { reason = JSON.parse(e.message)?.detail ?? e.message; } catch {}
      setPlanError(String(reason).slice(0, 300));
    }
    setBusy(false);
  }

  async function approveFundingPlan() {
    if (!fundingPlan || !window.confirm("Approve this exact plan version and its listed conversions? No payment will be sent.")) return;
    setBusy(true); setPlanError("");
    try {
      const approved = await api.approvePlan(fundingPlan.id, fundingPlan.version);
      setFundingPlan(approved);
      setFundingPlans((plans) => plans.map((item) => item.id === approved.id ? approved : item));
    } catch (e: any) {
      let reason = e.message;
      try { reason = JSON.parse(e.message)?.detail ?? e.message; } catch {}
      setPlanError(String(reason).slice(0, 300));
    }
    setBusy(false);
  }

  async function executeFundingPlan() {
    if (!fundingPlan) return;
    const paperExecution = capabilities?.capabilities?.dust_execution?.status === "paper_only";
    if (fundingPlan.steps?.length && !paperExecution) {
      setPlanError("Authenticated live small-balance conversion is gated until account-level verification succeeds.");
      return;
    }
    if (!window.confirm(`Execute plan v${fundingPlan.version}? This prepares USDC only; it does not send the payment.`)) return;
    setBusy(true); setPlanError("");
    try {
      const operationId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `plan-${Date.now()}`;
      await api.executePlan(fundingPlan.id, fundingPlan.version, operationId);
      setFundingPlan(await api.plan(fundingPlan.id));
      setAffordResult(await api.affordability({
        amount: parseFloat(affordAmount) || 0,
        minimum_reserve: parseFloat(affordReserve) || 0,
        recipient: affordRecipient || undefined,
        obligation_id: affordObligationId,
      }));
      await refresh();
    } catch (e: any) {
      let reason = e.message;
      try { reason = JSON.parse(e.message)?.detail ?? e.message; } catch {}
      setPlanError(String(reason).slice(0, 300));
    }
    setBusy(false);
  }

  async function saveObligation() {
    setBusy(true); setAffordError("");
    try {
      const created = await api.addObligation({ amount: parseFloat(affordAmount) || 0, asset: "USDC", recipient: affordRecipient || undefined, memo: obligationMemo });
      setAffordObligationId(created.id);
      await refresh();
      setAffordResult(await api.affordability({
        amount: parseFloat(affordAmount) || 0,
        minimum_reserve: parseFloat(affordReserve) || 0,
        recipient: affordRecipient || undefined,
        obligation_id: created.id,
      }));
      setFundingPlan(null);
    } catch (e: any) {
      setAffordError(String(e.message).slice(0, 300));
      setBusy(false);
    }
  }

  async function toggleProtection(asset: string, current: boolean) {
    setBusy(true);
    try { await api.assetPolicy(asset, !current); await refresh(); }
    finally { setBusy(false); }
  }

  function useObligation(obligation: any) {
    setAffordObligationId(obligation.id);
    setAffordAmount(String(obligation.amount));
    setAffordRecipient(obligation.recipient ?? "");
    setObligationMemo(obligation.memo ?? "");
    setAffordResult(null);
    setFundingPlan(null);
    setPlanError("");
  }

  function selectPayObligation(id: string) {
    if (!id) { setPayObligationId(undefined); return; }
    const obligation = obligations.find((item) => item.id === Number(id));
    if (!obligation) return;
    setPayObligationId(obligation.id);
    setPayAmt(String(obligation.amount));
    setPayTo(obligation.recipient ?? "");
    setPayMemo(obligation.memo ?? "");
    setPayPreview(null);
  }

  const total = portfolio?.total_priced_usdc ?? 0;
  const rows = portfolio?.holdings ?? [];
  const balSpot = bal?.mode === "live-exchange" ? bal?.exchange?.balances ?? {} : bal?.paper?.spot ?? {};
  const earnNote = (() => {
    const e = sweepResult?.earn;
    if (e && e.ok !== false && e.swept) return `swept $${fmt(e.swept)} to Flexible Earn (${e.source})`;
    if (e && e.ok === false) return e.error ?? e.reason ?? "earn failed";
    if (e && e.reason) return e.reason;
    const d = digest?.earn;
    if (d && d.principal !== undefined) return `Flexible holds $${fmt(d.principal)} at ${d.apr_pct}% APR (${d.source})`;
    return d?.reason ?? "earn checked";
  })();
  const confirmBlockedReason = !payPreview ? "Run Preview first." : !payPreview.ok ? payPreview.error : "";

  return (
    <main className="max-w-7xl mx-auto p-4 md:p-6 space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3 pt-2">
        <div>
          <p className="eyebrow mb-1.5">Cassa desk</p>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-extrabold tracking-tight">Command the vault</h1>
          <span className={`text-xs px-2 py-1 rounded-full ${online ? "bg-green-900 text-green-300" : online === false ? "bg-red-900 text-red-300" : "bg-zinc-800 text-zinc-400"}`}>
            {online ? `● live · ${bal?.mode ?? portfolio?.mode ?? ""}` : online === false ? "● backend offline" : "● connecting"}
          </span>
          {health && <span className="text-xs text-zinc-500">earn {health.rails?.earn} · x402 {health.rails?.x402}</span>}
          </div>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <label className="flex items-center gap-2 bg-zinc-900 border border-zinc-800 rounded-xl px-3 py-2">
            <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} />
            Dry-run {dryRun ? "ON (safe)" : "OFF (moves funds)"}
          </label>
          <button className="btn-ghost" onClick={refresh}>Refresh</button>
        </div>
      </header>

      {online === false && (
        <div className="card">Backend not reachable. Run: <code className="text-xs">cd /Users/apple/Documents/cassa && MOCK_MODE=true .venv/bin/python -m uvicorn backend.main:app --port 8000</code></div>
      )}

      <div className="ticker-tape border-y hairline bg-black/40 overflow-hidden">
        <div className="flex items-center">
          <span className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-[0.18em] text-emerald-400 px-3 py-2 border-r hairline shrink-0">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> Live
          </span>
          <div className="overflow-hidden flex-1">
            {markets.length === 0 ? (
              <p className="text-xs text-zinc-500 px-4 py-2">Connecting to the live feed…</p>
            ) : (
              <div className="ticker-track flex w-max whitespace-nowrap">
                {[...markets, ...markets].map((m, i) => (
                  <span key={i} className="text-xs font-mono px-5 py-2">
                    <span className="text-zinc-400">{m.asset}</span>{" "}
                    <span className="font-bold text-zinc-100">${fmt(m.price)}</span>{" "}
                    <span className={m.change_24h_pct >= 0 ? "text-green-400" : "text-red-400"}>
                      {m.change_24h_pct >= 0 ? "▲" : "▼"}{fmt(m.change_24h_pct)}%
                    </span>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <div className="space-y-4">
          <section className="card">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">Balance · {bal?.mode ?? "…"}</h2>
              <span className="text-xs text-zinc-500">source: {bal?.source ?? "…"} · valued at live prices</span>
            </div>
            <div className="text-3xl font-extrabold mt-1">${fmt(total)}</div>
            <div className="mt-3 divide-y divide-zinc-800">
              {rows.map((r: any) => (
                <div key={r.asset} className="flex justify-between py-1.5 text-sm">
                  <span className="font-mono">{r.asset} <span className="text-zinc-500">{r.quantity}</span></span>
                  <span className="flex items-center gap-2">
                    <span>{r.value_usdc == null ? "unpriced" : `$${fmt(r.value_usdc)}`}</span>
                    {r.dust_eligible && <span className="text-[10px] rounded-full bg-emerald-950 text-emerald-300 px-2 py-0.5">recover ${fmt(r.recoverable_usdc)}</span>}
                    {r.asset !== "USDC" && <button className="text-[10px] text-zinc-400 hover:text-white" disabled={busy} onClick={() => toggleProtection(r.asset, r.protected)}>{r.protected ? "Unprotect" : "Protect"}</button>}
                  </span>
                </div>
              ))}
              {rows.length === 0 && <p className="text-sm text-zinc-500">No holdings returned.</p>}
            </div>
            <div className="grid grid-cols-3 gap-2 mt-3 text-xs">
              <div className="bg-black/30 rounded-xl p-3"><span className="text-zinc-500 block">Free USDC</span><strong>${fmt(portfolio?.free_usdc)}</strong></div>
              <div className="bg-black/30 rounded-xl p-3"><span className="text-zinc-500 block">Reserved</span><strong>${fmt(portfolio?.reserved_usdc)}</strong></div>
              <div className="bg-black/30 rounded-xl p-3"><span className="text-zinc-500 block">Spendable</span><strong>${fmt(portfolio?.spendable_after_reservations_usdc)}</strong></div>
            </div>
            <p className="text-xs text-zinc-500 mt-2">Dust discovery: {portfolio?.dust?.source ?? portfolio?.dust?.reason ?? "…"} · execution {capabilities?.capabilities?.dust_execution?.status ?? "unknown"}</p>
            <div className="mt-3 border-t hairline pt-3">
              <div className="flex items-center justify-between text-sm">
                <span className="font-semibold">Flexible Earn · USDC</span>
                <span className="text-zinc-400">{bal?.earn ? `${fmt(bal.earn.principal)} @ ${bal.earn.apr_pct}% APR (${bal.earn.source})` : "…"}</span>
              </div>
              {bal?.earn?.accrued_total > 0 && (
                <p className="text-xs text-green-400 mt-1">+${fmt(bal.earn.accrued_total)} accrued in the paper ledger</p>
              )}
              <div className="flex gap-2 mt-2">
                <input className="input" value={redeemAmt} onChange={(e) => setRedeemAmt(e.target.value)} inputMode="decimal" placeholder="Amount USDC" />
                <button className="btn" disabled={busy} onClick={redeemEarn}>{dryRun ? "Preview redeem" : "Redeem"}</button>
              </div>
              {redeemResult && (
                <p className={`text-sm mt-2 ${redeemResult.ok ? "" : "text-red-400"}`}>
                  {redeemResult.ok ? ` principal left $${fmt(redeemResult.principal_left ?? redeemResult.principal_available ?? 0)}` : `Blocked: ${redeemResult.error}`}
                </p>
              )}
            </div>
          </section>

          <section className="card border-yellow-400/20">
            <p className="eyebrow mb-1">Decision workspace</p>
            <h2 className="font-semibold text-xl">Can I afford this?</h2>
            <p className="text-sm text-zinc-400">Checks cash, other obligations, your reserve, policy, and eligible small-balance recovery. This never moves funds.</p>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-2 mt-3">
              <label className="text-xs">Expense USDC<input className="input mt-1" value={affordAmount} onChange={(e) => { setAffordAmount(e.target.value); setAffordObligationId(undefined); }} inputMode="decimal" /></label>
              <label className="text-xs">Keep as reserve<input className="input mt-1" value={affordReserve} onChange={(e) => setAffordReserve(e.target.value)} inputMode="decimal" /></label>
              <label className="text-xs">Recipient<select className="input mt-1" value={affordRecipient} onChange={(e) => setAffordRecipient(e.target.value)}><option value="">Cash goal only</option>{Object.keys(book).map((k) => <option key={k} value={k}>@{k}</option>)}</select></label>
              <label className="text-xs">Obligation memo<input className="input mt-1" value={obligationMemo} onChange={(e) => setObligationMemo(e.target.value)} /></label>
            </div>
            <div className="flex flex-wrap gap-2 mt-3">
              <button className="btn" disabled={busy} onClick={checkAffordability}>Check affordability</button>
              <button className="btn-ghost" disabled={busy} onClick={saveObligation}>Reserve as obligation</button>
            </div>
            {affordObligationId && <p className="text-xs text-yellow-300 mt-2">Funding obligation #{affordObligationId}; its reservation is excluded once from this calculation.</p>}
            {affordError && <p className="text-red-400 text-sm mt-2">{affordError}</p>}
            {affordResult && (
              <div className="mt-4 space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`text-sm font-bold px-3 py-1 rounded-full ${affordResult.outcome === "affordable_now" ? "bg-emerald-950 text-emerald-300" : affordResult.outcome === "affordable_after_conversions" ? "bg-yellow-950 text-yellow-300" : "bg-red-950 text-red-300"}`}>{String(affordResult.outcome).replaceAll("_", " ")}</span>
                  <span className="text-xs text-zinc-500">payment: {affordResult.payment_status}</span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
                  {[['Free', affordResult.free_usdc], ['Other obligations', affordResult.other_obligations_usdc], ['Reserve', affordResult.minimum_reserve_usdc], ['Shortfall', affordResult.shortfall_usdc], ['After plan', affordResult.projected_headroom_usdc]].map(([label, value]) => <div key={label} className="bg-black/30 rounded-xl p-3"><span className="text-zinc-500 block">{label}</span><strong>${fmt(value)}</strong></div>)}
                </div>
                {affordResult.selected_conversions?.length > 0 && <div className="text-sm"><span className="text-zinc-400">Proposed recovery: </span>{affordResult.selected_conversions.map((c: any) => `${c.asset} ${c.quantity} → est. $${fmt(c.net_usdc)} net`).join(" · ")}</div>}
                <p className="text-xs text-zinc-500">Conversion values are estimates. Recipient settlement is currently limited to the verified internal-transfer adapter.</p>
                {['affordable_now', 'affordable_after_conversions'].includes(affordResult.outcome) && !fundingPlan && (
                  <button className="btn" disabled={busy} onClick={createFundingPlan}>Create reviewable funding plan</button>
                )}
              </div>
            )}
            {planError && <p className="text-red-400 text-sm mt-3">Plan: {planError}</p>}
            {fundingPlan && (
              <div className="mt-4 rounded-2xl border border-yellow-400/30 bg-yellow-950/10 p-4 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="eyebrow">Immutable plan · v{fundingPlan.version}</p>
                    <h3 className="font-semibold">{String(fundingPlan.state).replaceAll('_', ' ')}</h3>
                  </div>
                  <span className="text-xs text-zinc-500">expires {new Date(fundingPlan.expires_at * 1000).toLocaleTimeString()}</span>
                </div>
                {fundingPlan.steps?.length === 0 ? (
                  <p className="text-sm text-emerald-300">No conversion is needed; existing spendable USDC covers the goal and reserve.</p>
                ) : (
                  <div className="space-y-1">
                    {fundingPlan.steps.map((step: any) => (
                      <div key={step.ordinal} className="flex flex-wrap justify-between gap-2 text-sm border-b border-zinc-800 py-1.5">
                        <span>{step.ordinal}. Convert the whole eligible {step.input.asset} balance ({step.input.quantity})</span>
                        <span className="text-zinc-400">est. ${fmt(step.input.net_usdc)} net · {step.state}</span>
                      </div>
                    ))}
                  </div>
                )}
                <p className="text-xs text-zinc-500">Approved cost ceiling: {fundingPlan.request.max_conversion_fee_pct}% · proceeds bound: {fundingPlan.request.max_slippage_pct ?? 1}% · settlement remains a separate confirmed action.</p>
                <div className="flex flex-wrap gap-2">
                  {fundingPlan.state === 'awaiting_approval' && <button className="btn" disabled={busy} onClick={approveFundingPlan}>Approve exact plan</button>}
                  {fundingPlan.state === 'approved' && <button className="btn" disabled={busy || (fundingPlan.steps?.length > 0 && capabilities?.capabilities?.dust_execution?.status !== 'paper_only')} onClick={executeFundingPlan}>{fundingPlan.steps?.length ? 'Execute paper recovery' : 'Mark funds prepared'}</button>}
                  {fundingPlan.state === 'blocked' && <span className="text-sm text-red-300">This plan cannot be approved. Change the amount, reserve, policy, or eligible assets and reassess.</span>}
                </div>
                {fundingPlan.result && (
                  <div className="text-sm">
                    <strong>{fundingPlan.result.funding_status === 'funds_prepared' ? 'Funds prepared.' : 'Plan needs attention.'}</strong>{' '}
                    Payment status: {String(fundingPlan.result.settlement_status ?? 'not_executed').replaceAll('_', ' ')}.
                    {fundingPlan.result.conversion?.receipts?.length > 0 && <span className="text-zinc-400"> {fundingPlan.result.conversion.receipts.length} provider receipts recorded.</span>}
                  </div>
                )}
              </div>
            )}
            {fundingPlans.length > 0 && (
              <div className="mt-4 border-t hairline pt-3">
                <h3 className="text-sm font-semibold">Recent funding plans</h3>
                {fundingPlans.slice(0, 5).map((plan) => (
                  <div key={plan.id} className="flex flex-wrap items-center justify-between gap-2 text-xs py-1.5 border-b border-zinc-800">
                    <span>v{plan.version} · ${fmt(plan.request.amount)} · {String(plan.state).replaceAll('_', ' ')} · {plan.steps.length} conversion{plan.steps.length === 1 ? '' : 's'}</span>
                    <button className="text-yellow-400 hover:underline" onClick={() => { setFundingPlan(plan); setPlanError(''); }}>Review</button>
                  </div>
                ))}
              </div>
            )}
            <div className="mt-4 border-t hairline pt-3">
              <h3 className="text-sm font-semibold">Reserved obligations ({obligations.filter((o) => ['reserved','ready'].includes(o.status)).length})</h3>
              {obligations.length === 0 ? <p className="text-xs text-zinc-500 mt-1">No obligations saved.</p> : obligations.slice(0, 5).map((o) => <div key={o.id} className="flex items-center justify-between gap-2 text-xs py-1.5 border-b border-zinc-800"><span>#{o.id} {o.memo || 'Obligation'} · {o.amount} {o.asset} {o.recipient ? `→ @${o.recipient}` : ''} {o.funding_plan_id ? '· plan linked' : ''}</span><span className="flex items-center gap-2"><span className={o.status === 'ready' ? 'text-emerald-300' : 'text-zinc-500'}>{o.status}</span>{['reserved','ready'].includes(o.status) && <button className="text-yellow-400 hover:underline" onClick={() => useObligation(o)}>Use</button>}</span></div>)}
            </div>
          </section>

          <section className="card">
            <h2 className="font-semibold">Optional investment allocation</h2>
            <p className="text-sm text-zinc-400">Separate from payment preparation: buys the selected allocation, then sends only post-trade surplus above the reserve to Flexible Earn. {earnNote}.</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-3">
              <label className="text-xs">DCA total $<input className="input mt-1" value={dcaTotal} onChange={(e) => setDcaTotal(e.target.value)} inputMode="decimal" /></label>
              <label className="text-xs">BTC %<input className="input mt-1" value={splitBtc} onChange={(e) => setSplitBtc(e.target.value)} inputMode="decimal" /></label>
              <label className="text-xs">ETH %<input className="input mt-1" value={splitEth} onChange={(e) => setSplitEth(e.target.value)} inputMode="decimal" /></label>
              <label className="text-xs">SOL %<input className="input mt-1" value={splitSol} onChange={(e) => setSplitSol(e.target.value)} inputMode="decimal" /></label>
            </div>
            <div className="flex gap-2 mt-3">
              <button className="btn" disabled={busy} onClick={runSweep}>{dryRun ? "Preview sweep" : "Execute sweep"}</button>
            </div>
            {sweepError && <p className="text-sm text-red-400 mt-2">Sweep rejected: {sweepError}</p>}
            {sweepResult && (
              <div className="mt-3 text-sm space-y-1">
                {sweepResult.dca_fills?.map((f: any, i: number) => (
                  <div key={i} className="flex justify-between border-b border-zinc-800 py-1">
                    <span>BUY {f.asset} <span className="text-zinc-500">{f.symbol} @ ${fmt(f.price)}</span></span>
                    <span>${fmt(f.quote_usdc, 0)} → {f.est_qty} <span className="text-zinc-500">({f.result?.source})</span></span>
                  </div>
                ))}
                <div className="py-1 text-zinc-300">Earn: {earnNote}</div>
                {(sweepResult.dust ?? []).map((d: any, i: number) => (
                  <div key={i} className="flex justify-between text-zinc-400"><span>Dust {d.asset} {d.qty} ({d.action}, report-only)</span><span>~${fmt(d.est_usdc)}</span></div>
                ))}
              </div>
            )}
          </section>

          <section className="card">
            <h2 className="font-semibold">Allowlist pay (internal transfer)</h2>
            <p className="text-sm text-zinc-400">Allowlisted destinations, caps enforced server-side, external sends rejected.</p>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-2 mt-3">
              <label className="text-xs">Linked obligation<select className="input mt-1" value={payObligationId ?? ""} onChange={(e) => selectPayObligation(e.target.value)}><option value="">None</option>{obligations.filter((o) => ['reserved','ready'].includes(o.status) && o.recipient).map((o) => <option key={o.id} value={o.id}>#{o.id} · {o.status} · {o.memo || `${o.amount} USDC`}</option>)}</select></label>
              <label className="text-xs">To<select className="input mt-1" value={payTo} onChange={(e) => setPayTo(e.target.value)}>
                {Object.keys(book).map((k) => <option key={k} value={k}>@{k} — {book[k].label}</option>)}
              </select></label>
              <label className="text-xs">Amount USDC<input className="input mt-1" value={payAmt} onChange={(e) => setPayAmt(e.target.value)} inputMode="decimal" /></label>
              <label className="text-xs">Memo<input className="input mt-1" value={payMemo} onChange={(e) => setPayMemo(e.target.value)} /></label>
            </div>
            <div className="flex flex-wrap gap-2 mt-3">
              <button className="btn-ghost" disabled={busy} onClick={previewPay}>1 · Preview</button>
              <button className="btn" disabled={busy || !payPreview?.ok} title={confirmBlockedReason} onClick={() => setShowConfirm(true)}>
                2 · Review &amp; confirm
              </button>
            </div>
            {!payPreview?.ok && confirmBlockedReason && <p className="text-xs text-zinc-500 mt-2">{confirmBlockedReason}</p>}
            {payPreview && (
              <div className="mt-2 text-sm">
                {payPreview.ok
                  ? <p>→ @{payTo} ({payPreview.to.label}) ${fmt(payPreview.amount, 0)} · rail {payPreview.rail} · confirm needed: {String(payPreview.needs_confirm)} · today ${fmt(payPreview.caps?.spent_today, 0)}/${fmt(payPreview.caps?.daily, 0)}</p>
                  : <p className="text-red-400">Blocked: {payPreview.error}</p>}
              </div>
            )}
            {payError && <p className="text-sm text-red-400 mt-2">{payError}</p>}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mt-3">
              <input className="input" placeholder="id (e.g. carol)" value={newId} onChange={(e) => setNewId(e.target.value)} />
              <input className="input" placeholder="Label (e.g. Carol — Editor)" value={newLabel} onChange={(e) => setNewLabel(e.target.value)} />
              <input className="input" placeholder="internal email/uid" value={newDest} onChange={(e) => setNewDest(e.target.value)} />
            </div>
            <div className="flex gap-2 mt-2">
              <button className="btn-ghost" onClick={addRecipient}>Add recipient</button>
            </div>
            {bookError && <p className="text-sm text-red-400 mt-2">Add rejected: {bookError}</p>}
          </section>

          <section className="card">
            <div className="flex items-center justify-between mb-2">
              <h2 className="font-semibold">Digest</h2>
              <a href="/activity" className="text-xs text-yellow-400 hover:underline">Full ledger →</a>
            </div>
            {digest ? (
              <div className="text-sm space-y-1">
                <p>{digest.headline}</p>
                <p className="text-zinc-400">Yield rail: {digest.earn?.reason ?? digest.earn?.feature} · {digest.recent_activity?.length ?? 0} recent records</p>
              </div>
            ) : <p className="text-sm text-zinc-500">Loading digest…</p>}
          </section>

          <section className="card">
            <div className="flex items-center justify-between mb-2">
              <h2 className="font-semibold">Activity — latest</h2>
              <a href="/activity" className="text-xs text-yellow-400 hover:underline">Full ledger →</a>
            </div>
            {activity.length === 0 ? <p className="text-sm text-zinc-500">Nothing recorded yet.</p> :
              activity.slice(0, 6).map((a: any) => (
                <div key={a.ledger_entry_id} className="flex justify-between text-sm border-b border-zinc-800 py-1.5">
                  <span>#{a.ledger_entry_id} {a.type === "pay" ? `Sent $${fmt(a.amount, 0)} ${a.asset} → @${a.to}` : a.summary ?? a.type} {a.ok === false ? <span className="text-red-400">· {a.reason}</span> : null}</span>
                  <span className="text-zinc-500">{a.recorded_at ? timeAgo(a.recorded_at) : ""} · {a.mode ?? a.rail ?? ""}</span>
                </div>
              ))}
          </section>
        </div>
      </div>

      {!chatOpen ? (
        <button
          onClick={() => { setChatOpen(true); setUnread(0); }}
          className="fixed bottom-5 right-5 z-50 flex items-center gap-2.5 bg-yellow-400 text-black font-bold rounded-full pl-2 pr-4 py-2 shadow-[0_12px_36px_-10px_rgba(250,204,21,0.6)] hover:brightness-110 transition"
          aria-label="Open chat with Cassa"
        >
          <img src="/logo-mark.svg" alt="" width="28" height="28" className="h-7 w-7 rounded-full" />
          Chat
          {unread > 0 && (
            <span className="min-w-5 min-h-5 px-1 rounded-full bg-black text-yellow-400 text-[11px] font-extrabold flex items-center justify-center">{unread}</span>
          )}
        </button>
      ) : (
        <div className="card fixed bottom-5 right-5 z-50 w-[min(92vw,384px)] h-[min(68vh,560px)] !p-4 flex flex-col shadow-2xl">
          <div className="flex items-center gap-2 mb-2">
            <img src="/logo-mark.svg" alt="Cassa" width="22" height="22" className="h-[22px] w-[22px] rounded-lg" />
            <h2 className="font-semibold text-sm">Chat with Cassa</h2>
            <button onClick={() => setChatOpen(false)} className="ml-auto text-zinc-500 hover:text-white text-xl leading-none px-2" aria-label="Minimize chat">–</button>
          </div>
          <div className="flex flex-wrap gap-1.5 my-2">
            {["balance", "sweep", "pay @alice 10 USDC", "prices BTC", "digest"].map((q) => (
              <button key={q} className="text-xs bg-zinc-800 hover:bg-zinc-700 rounded-full px-3 py-1" onClick={() => send(q)}>{q}</button>
            ))}
          </div>
          <div ref={scrollRef} className="flex-1 overflow-auto space-y-3 my-2 pr-1">
            {msgs.map((m, i) => (
              <div key={i} className={`msg-in flex gap-2 ${m.role === "you" ? "flex-row-reverse" : ""}`}>
                {m.role === "cassa" ? (
                  <img src="/logo-mark.svg" alt="Cassa" width="24" height="24" className="h-6 w-6 rounded-lg mt-0.5 shrink-0" />
                ) : (
                  <span className="h-6 w-6 rounded-lg mt-0.5 shrink-0 bg-white/10 border border-white/15" />
                )}
                <div className={`max-w-[86%] ${m.role === "you" ? "text-right" : ""}`}>
                  {m.role === "cassa" && m.kind && (
                    <div className="text-[10px] uppercase tracking-[0.18em] text-zinc-500 mb-1">{m.kind}{m.via ? ` · ${m.via}` : ""}</div>
                  )}
                  <div className={`inline-block px-3 py-2 rounded-xl text-sm whitespace-pre-wrap text-left ${m.role === "you" ? "bg-yellow-400 text-black" : "bg-zinc-800 border border-white/[0.06]"}`}>{m.text}</div>
                  {m.at && (
                    <div className="text-[10px] text-zinc-600 mt-1">
                      {new Date(m.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {busy && (
              <div className="msg-in flex gap-2">
                <img src="/logo-mark.svg" alt="" width="24" height="24" className="h-6 w-6 rounded-lg mt-0.5 shrink-0" />
                <div className="bg-zinc-800 border border-white/[0.06] rounded-xl px-4 py-3.5 flex gap-1.5 items-center" aria-label="Cassa is typing">
                  {[0, 1, 2].map((d) => (
                    <span key={d} className="typing-dot h-1.5 w-1.5 rounded-full bg-zinc-400" style={{ animationDelay: `${d * 0.18}s` }} />
                  ))}
                </div>
              </div>
            )}
          </div>
          <div className="flex gap-2">
            <input className="input" value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send(input)} placeholder="balance · sweep · pay @bob 10 USDC" />
            <button className="btn" disabled={busy} onClick={() => send(input)}>Send</button>
          </div>
          <p className="text-[11px] text-zinc-500 mt-2">Dry-run {dryRun ? "ON" : "OFF"} · caps $500/send</p>
        </div>
      )}

      {showConfirm && payPreview?.ok && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="card max-w-md w-full space-y-3">
            <h3 className="font-bold text-lg">Confirm send</h3>
            <div className="text-sm divide-y divide-zinc-800">
              <div className="flex justify-between py-1.5"><span className="text-zinc-400">To</span><span>@{payTo} ({payPreview.to.label})</span></div>
              <div className="flex justify-between py-1.5"><span className="text-zinc-400">Amount</span><span>${fmt(payPreview.amount, 0)} {payPreview.asset}</span></div>
              <div className="flex justify-between py-1.5"><span className="text-zinc-400">Memo</span><span>{payPreview.memo || "—"}</span></div>
              <div className="flex justify-between py-1.5"><span className="text-zinc-400">Rail</span><span>{payPreview.rail}</span></div>
              <div className="flex justify-between py-1.5"><span className="text-zinc-400">Mode</span><span>{dryRun ? "dry-run (no funds move)" : "LIVE (funds move)"}</span></div>
            </div>
            <div className="flex gap-2">
              <button className="btn-ghost flex-1" disabled={busy} onClick={() => setShowConfirm(false)}>Cancel</button>
              <button className="btn flex-1" disabled={busy} onClick={confirmPay}>Confirm send</button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
