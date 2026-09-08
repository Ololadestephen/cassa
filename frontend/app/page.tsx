"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api";

const GITHUB_URL = process.env.NEXT_PUBLIC_GITHUB_URL || "https://github.com/Ololadestephen/cassa";

const DECISIONS = [
  ["01", "Read the whole account", "Free, locked, reserved, protected, unpriced, and route-eligible funds stay distinct."],
  ["02", "Decide what may move", "Cassa subtracts obligations and the reserve before it considers a conversion."],
  ["03", "Use only what is needed", "Available routes, minimums, and costs determine the smallest sufficient funding plan."],
  ["04", "Ask before acting", "Approval is tied to the exact assets, amounts, limits, recipient, and expiry."],
  ["05", "Prove the outcome", "Provider receipts and balance reconciliation show what happened—and prevent blind retries."],
];

const INDEX = [
  ["Account", "Every non-zero holding, across the wallet surfaces the connection permits."],
  ["Market", "Live prices and route availability, including assets outside the usual major-coin list."],
  ["Policy", "Protected holdings, obligations, recipients, spend caps, and the minimum reserve."],
  ["Plan", "The least disruptive sequence that can make the requested amount ready."],
  ["Approval", "A fixed plan version. Changing the plan voids the approval."],
  ["Evidence", "Receipts, actual charges, provider IDs, and unresolved outcomes."],
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

  const runtime = down || !health ? "Runtime unavailable" : health.mock_mode ? "Paper execution" : "Live exchange";
  const reserve = config ? `${Number(config.minimum_reserve_usdc).toLocaleString()} USDC` : "Set by owner";
  const recipients = Object.keys(book).length ? `${Object.keys(book).length} allowlisted` : "Owner controlled";

  return (
    <main className="margin-book">
      <div className="book-shell">
        <nav className="book-nav" aria-label="Main navigation">
          <a href="/" className="book-wordmark" aria-label="Cassa home">
            CASSA<span>◆</span>
          </a>
          <p className="book-nav-note">Cash control for Binance agents</p>
          <div className="book-nav-links">
            <a href="/policy">Rules</a>
            <a href="/activity">Evidence</a>
            <a href="/app" className="book-nav-cta">Enter the ledger</a>
          </div>
        </nav>

        <header className="book-hero">
          <div className="book-hero-copy">
            <p className="book-kicker">A cash-readiness agent · Built with Binance Agent OS</p>
            <h1>
              What can safely
              <br />
              <em>leave the account?</em>
            </h1>
            <p className="book-lede">
              A wallet balance answers the wrong question. Cassa reads the funds, obligations,
              protected holdings, minimums, and costs—then prepares only what the payment needs.
            </p>
            <div className="book-actions">
              <a href="/app" className="book-primary">Check what&apos;s spendable <span>→</span></a>
              <a href="#method" className="book-secondary">See how Cassa decides</a>
            </div>
            <p className="book-fineprint">Reading is immediate. Anything that moves money requires an exact review.</p>
          </div>

          <aside className="decision-sheet" aria-label="Cassa decision anatomy">
            <div className="sheet-topline">
              <span>DECISION NOTE / 001</span>
              <span className="sheet-stamp">READ FIRST</span>
            </div>
            <p className="sheet-prompt">“Can I fund this payment and keep my reserve?”</p>
            <div className="sheet-rule" />
            <div className="sheet-row"><span>Start with</span><strong>spendable stablecoin</strong></div>
            <div className="sheet-row"><span>Keep aside</span><strong>obligations + reserve</strong></div>
            <div className="sheet-row"><span>Never touch</span><strong>protected assets</strong></div>
            <div className="sheet-row"><span>Recover</span><strong>only the remaining shortfall</strong></div>
            <div className="sheet-row"><span>Exclude</span><strong>unpriced / below minimum</strong></div>
            <div className="sheet-result">
              <span>CASSA RETURNS</span>
              <strong>A bounded plan, not a blanket sell order.</strong>
            </div>
            <div className="sheet-signoff">
              <span>approval ≠ intent</span>
              <span>receipt ≠ estimate</span>
            </div>
          </aside>
        </header>

        <section className="proof-strip" aria-label="Current product evidence">
          <div><span>Connection</span><strong>Agent OS OAuth verified</strong></div>
          <div><span>Runtime</span><strong>{runtime}</strong></div>
          <div><span>Reserve rule</span><strong>{reserve}</strong></div>
          <div><span>Recipients</span><strong>{recipients}</strong></div>
        </section>

        <section className="book-manifesto">
          <p className="book-section-label">The problem</p>
          <blockquote>
            Agents can access money.
            <br />
            <span>Access is not judgment.</span>
          </blockquote>
          <div className="manifesto-copy">
            <p>
              Trading and payment tools can execute an instruction. They do not automatically know
              whether the funds are already promised, whether a token should be protected, whether a
              route minimum makes it unusable, or whether a timed-out action already succeeded.
            </p>
            <p>
              Cassa sits before execution. It turns a financial goal into a constrained, inspectable
              sequence—and refuses the sequence when the evidence is not good enough.
            </p>
          </div>
        </section>

        <section id="method" className="book-method">
          <div className="book-method-head">
            <p className="book-section-label">The method</p>
            <h2>One request.<br />Five accountable decisions.</h2>
            <p>Each line exists because real money can be duplicated, stranded, or spent twice when an agent guesses.</p>
          </div>
          <ol className="ledger-sequence">
            {DECISIONS.map(([number, title, body]) => (
              <li key={number}>
                <span className="ledger-number">{number}</span>
                <h3>{title}</h3>
                <p>{body}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="book-index">
          <div className="index-intro">
            <p className="book-section-label">Inside the decision</p>
            <h2>Not another<br />“sell all” button.</h2>
            <p>
              Small-balance recovery is one possible step. Sometimes the correct answer is to use
              stablecoin already available. Sometimes it is to exclude an asset. Sometimes it is to stop.
            </p>
            <a href="/policy">Read the enforced rules →</a>
          </div>
          <dl className="capability-index">
            {INDEX.map(([term, description], index) => (
              <div key={term}>
                <dt><span>{String(index + 1).padStart(2, "0")}</span>{term}</dt>
                <dd>{description}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="book-demo">
          <p className="book-section-label">The live question</p>
          <div className="demo-question">
            <span>ASK CASSA</span>
            <p>“Can I prepare this payment, protect what matters, and still have enough left?”</p>
          </div>
          <div className="demo-answer">
            <span>THE ANSWER INCLUDES</span>
            <p>What is spendable. What is excluded. What must convert. What it costs. What remains. What needs approval.</p>
          </div>
        </section>

        <section className="book-close">
          <div>
            <p className="book-section-label">Start with a read</p>
            <h2>Know before money moves.</h2>
          </div>
          <a href="/app" className="book-primary book-primary-dark">Check what&apos;s spendable <span>→</span></a>
        </section>

        <footer className="book-footer">
          <p>Cassa does not provide financial advice. Provider access, account eligibility, and jurisdictional restrictions apply.</p>
          <div>
            <a href="/app">Ledger</a>
            <a href="/policy">Rules</a>
            <a href="/activity">Evidence</a>
            <a href={GITHUB_URL}>GitHub</a>
          </div>
        </footer>
      </div>
    </main>
  );
}
