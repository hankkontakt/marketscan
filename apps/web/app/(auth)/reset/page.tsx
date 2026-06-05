"use client";

import { useState } from "react";
import Link from "next/link";
import { TrendingUp } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

export default function ResetPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");
  const supabase = createClient();

  async function handleReset(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/update-password`,
    });
    if (error) { setError(error.message); setLoading(false); }
    else setDone(true);
  }

  return (
    <div className="min-h-dvh flex items-center justify-center p-4"
         style={{ background: "var(--color-bg-base)" }}>
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center mb-3"
               style={{ background: "var(--color-accent-soft)", border: "1px solid var(--color-border)" }}>
            <TrendingUp size={22} strokeWidth={1.5} style={{ color: "var(--color-accent)" }} />
          </div>
          <h1 className="text-xl font-bold text-[var(--color-text-primary)]">MarketScan</h1>
        </div>
        <div className="rounded-2xl p-6 border"
             style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
          {done ? (
            <div className="text-center space-y-3">
              <p className="text-sm" style={{ color: "var(--color-up)" }}>Länk skickad!</p>
              <p className="text-xs text-[var(--color-text-muted)]">Kontrollera din e-post.</p>
              <Link href="/login" className="block text-xs text-[var(--color-accent)] hover:underline">
                Tillbaka till inloggning
              </Link>
            </div>
          ) : (
            <>
              <h2 className="text-sm font-semibold mb-4 text-[var(--color-text-primary)]">
                Återställ lösenord
              </h2>
              <form onSubmit={handleReset} className="space-y-4">
                <div>
                  <label className="text-xs mb-1 block text-[var(--color-text-secondary)]">E-post</label>
                  <input
                    type="email" value={email} onChange={(e) => setEmail(e.target.value)} required
                    className="w-full h-9 px-3 rounded-lg text-sm border bg-[var(--color-bg-elevated)]
                               border-[var(--color-border)] text-[var(--color-text-primary)]
                               focus:border-[var(--color-accent)] focus:outline-none"
                  />
                </div>
                {error && <p className="text-xs text-[var(--color-down)]">{error}</p>}
                <button type="submit" disabled={loading}
                        className="w-full h-9 rounded-lg text-sm font-medium bg-[var(--color-accent)]
                                   text-white hover:bg-[var(--color-accent-hover)] disabled:opacity-50">
                  {loading ? "Skickar..." : "Skicka återställningslänk"}
                </button>
              </form>
              <p className="mt-4 text-center text-xs text-[var(--color-text-muted)]">
                <Link href="/login" className="text-[var(--color-accent)] hover:underline">
                  Tillbaka till inloggning
                </Link>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
