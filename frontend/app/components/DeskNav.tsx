import Link from "next/link";

export function DeskNav() {
  return (
    <nav className="desk-nav sticky top-0 z-40 border-b" aria-label="Cassa workspace">
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-3 flex items-center gap-1 text-sm">
        <Link href="/" className="font-black tracking-[0.14em] text-sm mr-5">
          CASSA<span className="desk-wordmark-mark ml-1">◆</span>
        </Link>
        <span className="desk-nav-note hidden md:inline text-[9px] uppercase tracking-[0.14em] mr-auto">cash-readiness ledger</span>
        <Link href="/app" className="px-3 py-1.5 transition">Decision</Link>
        <Link href="/policy" className="px-3 py-1.5 transition">Rules</Link>
        <Link href="/activity" className="px-3 py-1.5 transition">Evidence</Link>
      </div>
    </nav>
  );
}
