export const API = process.env.NEXT_PUBLIC_API || "http://localhost:8000";
async function j(res: Response) {
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
export const api = {
  health: () => fetch(`${API}/api/health`).then(j),
  market: () => fetch(`${API}/api/market`).then(j),
  balance: () => fetch(`${API}/api/balance`).then(j),
  portfolio: () => fetch(`${API}/api/portfolio`).then(j),
  capabilities: () => fetch(`${API}/api/capabilities`).then(j),
  affordability: (body: { amount: number; payment_fee?: number; minimum_reserve?: number; obligation_id?: number; recipient?: string; allowed_assets?: string[] }) =>
    fetch(`${API}/api/affordability`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(j),
  plans: () => fetch(`${API}/api/plans`).then(j),
  plan: (id: string) => fetch(`${API}/api/plans/${encodeURIComponent(id)}`).then(j),
  createPlan: (body: { amount: number; payment_fee?: number; minimum_reserve?: number; obligation_id?: number; recipient?: string; allowed_assets?: string[]; max_conversion_fee_pct?: number; max_slippage_pct?: number; validity_seconds?: number }) =>
    fetch(`${API}/api/plans`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(j),
  approvePlan: (id: string, version: number) =>
    fetch(`${API}/api/plans/${encodeURIComponent(id)}/approve`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ version, confirmed: true }) }).then(j),
  executePlan: (id: string, version: number, operationId: string) =>
    fetch(`${API}/api/plans/${encodeURIComponent(id)}/execute`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ version, operation_id: operationId }) }).then(j),
  obligations: () => fetch(`${API}/api/obligations`).then(j),
  addObligation: (body: { amount: number; asset?: string; due_date?: string; recipient?: string; memo?: string }) =>
    fetch(`${API}/api/obligations`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(j),
  updateObligation: (id: number, status: string) =>
    fetch(`${API}/api/obligations/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) }).then(j),
  assetPolicy: (asset: string, protectedAsset: boolean, minimumKeep = 0) =>
    fetch(`${API}/api/asset-policies/${encodeURIComponent(asset)}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ protected: protectedAsset, minimum_keep: minimumKeep }) }).then(j),
  digest: () => fetch(`${API}/api/digest`).then(j),
  activity: () => fetch(`${API}/api/activity`).then(j),
  receipts: () => fetch(`${API}/api/receipts`).then(j),
  reconciliations: () => fetch(`${API}/api/reconciliations`).then(j),
  resolveFailed: (operationId: string, evidence: string) =>
    fetch(`${API}/api/reconciliations/${encodeURIComponent(operationId)}/resolve-failed`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ evidence, confirmed: true }) }).then(j),
  config: () => fetch(`${API}/api/config`).then(j),
  sweep: (body: { dca_total_usdc: number; dca_split: Record<string, number>; sweep_idle_over_usdc: number; dust_under_usdc: number; dry_run: boolean; confirmed?: boolean; operation_id?: string }) =>
    fetch(`${API}/api/sweep`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(j),
  chat: (message: string, dry_run = true) =>
    fetch(`${API}/api/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message, dry_run }) }).then(j),
  pay: (to: string, amount: number, asset = "USDC", memo = "", dry_run = true, confirmed = false, operationId?: string, obligationId?: number) =>
    fetch(`${API}/api/pay`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ to, amount, asset, memo, dry_run, confirmed, operation_id: operationId, obligation_id: obligationId }) }).then(j),
  earnPositions: () => fetch(`${API}/api/earn/positions`).then(j),
  earnRedeem: (amount: number, dry_run = true, confirmed = false) =>
    fetch(`${API}/api/earn/redeem`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ asset: "USDC", amount, dry_run, confirmed }) }).then(j),
  addRecipient: (id: string, label: string, email_or_uid: string) =>
    fetch(`${API}/api/addressbook`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id, label, email_or_uid }) }).then(j),
};
export function timeAgo(ts: number) {
  const s = Math.floor(Date.now() / 1000 - ts);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}
