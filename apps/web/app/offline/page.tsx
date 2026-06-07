import Link from "next/link";
import { WifiOff } from "lucide-react";

export default function OfflinePage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg-base)]">
      <div className="text-center space-y-4 max-w-sm">
        <WifiOff size={40} strokeWidth={1.5} className="text-[var(--color-text-muted)] mx-auto" />
        <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">
          Ingen anslutning
        </h1>
        <p className="text-sm text-[var(--color-text-muted)] leading-relaxed">
          MarketScan fungerar bäst med internet. Försök igen när du har en stabil anslutning.
        </p>
        <Link
          href="/oversikt"
          className="inline-block px-4 py-2 rounded-lg text-sm font-medium text-white bg-[var(--color-accent)]"
        >
          Försök igen
        </Link>
      </div>
    </div>
  );
}
