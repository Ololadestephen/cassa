"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

const ONE_LINER =
  "Turn scattered Binance balances into payment-ready cash while protecting the holdings and reserves that matter.";
const GITHUB_URL = process.env.NEXT_PUBLIC_GITHUB_URL || "";

function StatusDot({ tone }: { tone: "live" | "off" | "mute" }) {
  const color = tone === "live" ? "bg-emerald-400" : tone === "off" ? "bg-red-400" : "bg-zinc-600";
  return (
    <span className="relative flex h-2 w-2">
      {tone === "live" && <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-60 ${color}`} />}
      <span className={`relative inline-flex rounded-full h-2 w-2 ${color}`} />
    </span>
  );
}

function ProofChip({ label, value, live }: { label: string; value: string; live: boolean | null }) {
  return (
    <div className="flex items-center gap-2.5 bg-white/[0.04] border border-white/10 rounded-full pl-3.5 pr-4 py-2 text-[13px]">
      <StatusDot tone={live === null ? "mute" : live ? "live" : "off"} />
      <span className="text-zinc-400">{label}</span>
      <span className="font-semibold text-zinc-100">{value}</span>
    </div>
  );
}

const FRAMES = [
  { n: "01", title: "Live market", body: "Spot ticks from the public feed, refreshed while you watch.", img: "/frame-market.svg" },
  { n: "02", title: "Affordability", body: "See free cash, obligations, reserve, shortfall, and recoverable balances in one decision.", img: "/frame-sweep.svg" },
  { n: "03", title: "Funding plan", body: "Protect tokens, estimate eligible recovery, and review the exact payment goal.", img: "/frame-pay.svg" },
  { n: "04", title: "Receipts", body: "Durable operation IDs prevent a completed payment from running twice.", img: "/frame-ledger.svg" },
];

const STEPS = [
  { n: "01", title: "Discover usable cash", body: "Separate free, reserved, protected, unpriced, and provider-eligible balances." },
  { n: "02", title: "Ask what you can afford", body: "Cassa calculates the shortfall after obligations, fees, and the reserve you choose." },
  { n: "03", title: "Approve a funding plan", body: "Review proposed conversions and settlement availability. Every live write needs confirmation." },
];

const RAILS: Array<[string, string, boolean]> = [
  ["Live public market data", "Prices, 24h stats, order book", true],
  ["Dynamic portfolio", "All nonzero Spot holdings, pricing gaps, reserves, and protection", true],
  ["Small-balance discovery", "USDC estimates in paper; live account access remains unverified", true],
  ["Internal transfer", "Implemented adapter; external teammate settlement is not claimed", true],
  ["Earn", "Paper fixture available; live account capability remains unverified", true],
  ["x402", "Gated — returns SKILL_UNAVAILABLE, recorded in the ledger", false],
];

export default function Landing() {
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

  const modeLabel = down || !health ? "status unknown" : health.mock_mode ? "paper ledger" : "live exchange";
  const earnLabel = down || !health ? "status unknown" : String(health.rails?.earn ?? "unknown");
  const x402Label = down || !health ? "status unknown" : String(health.rails?.x402 ?? "unknown");
  const perPay = config ? `$${Number(config.max_per_pay_usdc).toLocaleString()}` : "status unknown";
  const daily = config ? `$${Number(config.max_daily_usdc).toLocaleString()}` : "status unknown";
  const confirmAt = config ? `$${Number(config.require_confirm_over_usdc).toLocaleString()}` : "status unknown";
  const x402cap = config ? `$${Number(config.max_x402_per_day_usdc).toLocaleString()}/day` : "status unknown";
  const reserve = config ? `$${Number(config.minimum_reserve_usdc).toLocaleString()}` : "status unknown";
  const allowlist = Object.keys(book);

  return (
    <main>
      <div className="relative max-w-6xl mx-auto px-5 md:px-8">
        <nav className="flex items-center justify-between py-6">
          <span className="font-extrabold tracking-tight text-lg">
            Cassaforte<span className="text-yellow-400">.</span>
          </span>
          <div className="flex items-center gap-2 text-sm">
            <a href="/policy" className="hidden sm:inline px-3 py-2 text-zinc-400 hover:text-white transition">Policy</a>
            <a href="/activity" className="hidden sm:inline px-3 py-2 text-zinc-400 hover:text-white transition">Ledger</a>
            <a href="/app" className="btn !px-5 !py-2.5 text-sm">Open the desk</a>
          </div>
        </nav>

        <header className="text-center pt-10 md:pt-16 pb-12 space-y-7">
          <p className="eyebrow">Binance Agent OS · Track A</p>
          <h1 className="font-extrabold tracking-tighter leading-[0.95] text-6xl md:text-8xl">
            Know what you can
            <br />
            <span className="text-yellow-400">actually afford.</span>
          </h1>
          <p className="text-lg md:text-xl text-zinc-400 max-w-2xl mx-auto leading-relaxed">{ONE_LINER}</p>
          <div className="flex flex-wrap justify-center gap-2.5 pt-1">
            <ProofChip label="mode" value={modeLabel} live={down || !health ? null : true} />
            <ProofChip label="earn" value={earnLabel} live={down || !health ? null : false} />
            <ProofChip label="x402" value={x402Label} live={down || !health ? null : false} />
          </div>
          <div className="flex items-center justify-center gap-3 pt-2">
            <a href="/app" className="btn !px-7 !py-3.5 text-base">Open the desk →</a>
            <a href="/policy" className="btn-ghost !px-6 !py-3.5 text-base">Read the policy</a>
          </div>
          <div className="card !p-3 max-w-3xl mx-auto text-left">
            <img src="/hero-desk.svg" alt="The Cassaforte cash-readiness desk" className="rounded-xl w-full" width="880" height="520" />
          </div>
          <p className="-mt-3 text-xs text-zinc-600">The desk — portfolio, affordability, obligations, approvals, and receipts.</p>
          {down && <p className="text-xs text-zinc-500">Backend unreachable — live figures show “status unknown” until it returns.</p>}
        </header>

        <section className="py-10">
          <p className="eyebrow mb-6 text-center">How it works</p>
          <div className="grid md:grid-cols-3 gap-4">
            {STEPS.map((s) => (
              <div key={s.n} className="card !p-7 relative overflow-hidden group hover:border-yellow-400/30 transition duration-200">
                <div className="text-5xl font-extrabold text-white/[0.07] absolute top-4 right-5 select-none">{s.n}</div>
                <div className="text-yellow-400 font-mono text-xs mb-3">{s.n}</div>
                <h3 className="font-bold text-lg mb-2">{s.title}</h3>
                <p className="text-sm text-zinc-400 leading-relaxed">{s.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="py-10 grid lg:grid-cols-2 gap-4">
          <div className="card !p-7">
            <p className="eyebrow mb-4">Agent OS surface</p>
            <ul className="space-y-3 text-sm">
              {RAILS.map(([title, body, on]) => (
                <li key={title} className="flex gap-3">
                  <span className={`mt-0.5 font-bold ${on ? "text-emerald-400" : "text-red-400"}`}>{on ? "✓" : "✕"}</span>
                  <span>
                    <span className="font-semibold">{title}</span>
                    <span className="text-zinc-500"> — {body}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
          <div className="card !p-7">
            <div className="flex items-center justify-between mb-4">
              <p className="eyebrow">Policy, live from the desk</p>
              <a href="/policy" className="text-xs text-yellow-400 hover:underline">Full policy →</a>
            </div>
            <div className="divide-y divide-white/[0.07] text-sm">
              {[
                ["Per-send hard veto", perPay],
                ["Daily ceiling", daily],
                ["Confirm at or above", confirmAt],
                ["Minimum operating reserve", reserve],
                ["x402 ceiling, if that skill ever connects", x402cap],
                ["Allowlist", allowlist.length ? allowlist.map((k) => `@${k}`).join("  ·  ") : "status unknown"],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4 py-3">
                  <span className="text-zinc-400">{k}</span>
                  <span className="font-mono text-right">{v}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="py-10">
          <p className="eyebrow mb-6 text-center">Inside the desk</p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {FRAMES.map((f) => (
              <a key={f.n} href="/app" className="card !p-5 hover:border-yellow-400/40 hover:-translate-y-0.5 transition duration-200 block group">
                <div className="rounded-xl mb-4 overflow-hidden border border-white/[0.07] bg-black/40">
                  <img src={f.img} alt={f.title} className="w-full h-28 object-cover" width="400" height="240" loading="lazy" />
                </div>
                <div className="font-bold text-sm">{f.title}</div>
                <div className="text-xs text-zinc-500 mt-1 leading-relaxed">{f.body}</div>
              </a>
            ))}
          </div>
        </section>

        <section className="py-14 text-center">
          <div className="card !p-10 md:!p-14 text-center">
            <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight">
              Prepare the cash. <span className="text-yellow-400">Protect the rest.</span>
            </h2>
            <p className="text-zinc-400 mt-3 max-w-xl mx-auto text-sm md:text-base">Start with a read-only affordability check. Every action that moves funds requires an explicit review.</p>
            <a href="/app" className="btn !px-8 !py-3.5 text-base mt-7 inline-flex relative">Open the desk →</a>
          </div>
        </section>

        <footer className="text-center text-xs text-zinc-600 space-y-2 pb-12 pt-4 border-t border-white/[0.07]">
          <p>Not financial advice. Cassaforte executes only what policy allows and refuses the rest.</p>
          <p>Unavailable in the US, UK, EEA, Hong Kong, Singapore, and other Binance restricted jurisdictions.</p>
          <p className="pt-1">
            <a href="/app" className="hover:text-zinc-300 transition">Desk</a>
            <span className="mx-2 text-zinc-700">·</span>
            <a href="/policy" className="hover:text-zinc-300 transition">Policy</a>
            <span className="mx-2 text-zinc-700">·</span>
            <a href="/activity" className="hover:text-zinc-300 transition">Ledger</a>
            {GITHUB_URL && (
              <>
                <span className="mx-2 text-zinc-700">·</span>
                <a href={GITHUB_URL} className="hover:text-zinc-300 transition">GitHub</a>
              </>
            )}
          </p>
        </footer>
      </div>
    </main>
  );
}
