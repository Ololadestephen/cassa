import Link from "next/link";

export function DeskNav() {
  return (
    <nav className="desk-nav sticky top-0 z-40 border-b border-[#d1ad43]/30 bg-[#0b0b09]/95" aria-label="Cassa workspace">
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-3 flex items-center gap-1 text-sm">
        <Link href="/" className="font-black tracking-[0.14em] text-sm mr-5">
          CASSA<span className="text-[#d85b42] ml-1">◆</span>
        </Link>
        <span className="hidden md:inline text-[9px] uppercase tracking-[0.14em] text-zinc-600 mr-auto">cash-readiness ledger</span>
        <Link href="/app" className="px-3 py-1.5 text-zinc-300 hover:text-[#e1b84d] transition">Decision</Link>
        <Link href="/policy" className="px-3 py-1.5 text-zinc-300 hover:text-[#e1b84d] transition">Rules</Link>
        <Link href="/activity" className="px-3 py-1.5 text-zinc-300 hover:text-[#e1b84d] transition">Evidence</Link>
      </div>
    </nav>
  );
}
