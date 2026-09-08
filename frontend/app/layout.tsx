import "./globals.css";

export const metadata = {
  title: "Cassa — Know what you can afford",
  description:
    "Cash readiness for Binance holdings: protect reserves, recover small balances, and prepare payment funds.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
