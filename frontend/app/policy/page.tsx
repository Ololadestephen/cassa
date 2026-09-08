"use client";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { DeskNav } from "../components/DeskNav";

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-4 py-3 border-b border-zinc-800 text-sm">
      <span className="text-zinc-400">{k}</span>
      <span className="font-mono text-right">{v}</span>
    </div>
  );
}

export default function PolicyPage() {
  const [health, setHealth] = useState<any>(null);
  const [config, setConfig] = useState<any>(null);
  const [book, setBook] = useState<Record<string, any>>({});
  const [down, setDown] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [h, c] = await Promise.all([api.health(), api.config()]);
        setHealth(h);
        setConfig(c.config);
        setBook(c.addressbook);
      } catch {
        setDown(true);
      }
    })();
  }, []);

  if (down) return <><DeskNav /><main className="desk-page max-w-4xl mx-auto p-6"><div className="card">Backend unreachable — policy unknown until it is back.</div></main></>;
  if (!health || !config) return <><DeskNav /><main className="desk-page max-w-4xl mx-auto p-6"><div className="card text-sm text-zinc-500">Loading live policy…</div></main></>;

  return (
    <><DeskNav /><main className="desk-page max-w-4xl mx-auto p-4 md:p-6 space-y-4">
      <header className="desk-page-header pt-5">
        <p className="eyebrow mb-1.5">Rule book / read only</p>
        <h1>What Cassa will refuse.</h1>
        <p>These are active constraints from the running ledger—not marketing promises. They are checked before an execution path opens.</p>
      </header>
      <section className="card">
        <h2 className="font-semibold mb-2">Caps</h2>
        <Row k="Per-send hard veto" v={`$${Number(config.max_per_pay_usdc).toLocaleString()}`} />
        <Row k="Daily ceiling" v={`$${Number(config.max_daily_usdc).toLocaleString()}`} />
        <Row k="Confirm at or above" v={`$${Number(config.require_confirm_over_usdc).toLocaleString()}`} />
        <Row k="Minimum operating reserve" v={`$${Number(config.minimum_reserve_usdc).toLocaleString()}`} />
        <Row k="x402 ceiling if that skill ever connects" v={`$${Number(config.max_x402_per_day_usdc).toLocaleString()}/day`} />
      </section>
      <section className="card">
        <h2 className="font-semibold mb-2">Allowlist ({Object.keys(book).length})</h2>
        {Object.entries(book).map(([id, r]: [string, any]) => (
          <Row key={id} k={`@${id} — ${r.label}`} v={`${r.asset} · ${r.rail}`} />
        ))}
        <p className="text-xs text-zinc-500 mt-2">Sends to anyone off this list are vetoed with the known names in the error.</p>
      </section>
      <section className="card">
        <h2 className="font-semibold mb-2">Rails</h2>
        <Row k="Market data" v={String(health.rails?.market_data ?? "unknown")} />
        <Row k="Spot" v={String(health.rails?.spot ?? "unknown")} />
        <Row k="Internal transfer" v={String(health.rails?.internal_transfer ?? "unknown")} />
        <Row k="Earn" v={String(health.rails?.earn ?? "unknown")} />
        <Row k="x402" v={String(health.rails?.x402 ?? "unknown")} />
        <Row k="External sends" v="rejected before any execute call" />
        <Row k="Mode" v={health.mock_mode ? "paper ledger" : "live exchange"} />
      </section>
    </main></>
  );
}
