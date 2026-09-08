import Link from "next/link";

export default function DeskLayout({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <nav className="sticky top-0 z-40 border-b border-white/[0.07] bg-[#08080A]/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-3 flex items-center gap-1 text-sm">
          <Link href="/" className="font-extrabold tracking-tight text-base mr-4">
            Cassa<span className="text-yellow-400">.</span>
          </Link>
          <Link href="/app" className="px-3 py-1.5 rounded-lg text-zinc-300 hover:text-white hover:bg-white/5 transition">
            Desk
          </Link>
          <Link href="/policy" className="px-3 py-1.5 rounded-lg text-zinc-300 hover:text-white hover:bg-white/5 transition">
            Policy
          </Link>
          <Link href="/activity" className="px-3 py-1.5 rounded-lg text-zinc-300 hover:text-white hover:bg-white/5 transition">
            Ledger
          </Link>
        </div>
      </nav>
      {children}
    </div>
  );
}
