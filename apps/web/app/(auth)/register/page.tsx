"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { TrendingUp } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const router = useRouter();
  const supabase = createClient();

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) {
      setError(error.message);
      setLoading(false);
    } else {
      setDone(true);
    }
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
          <p className="text-xs mt-1 text-[var(--color-text-muted)]">Skapa konto</p>
        </div>

        <div className="rounded-2xl p-6 border"
             style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
          {done ? (
            <div className="text-center space-y-3">
              <p className="text-sm text-[var(--color-up)]">Konto skapat!</p>
              <p className="text-xs text-[var(--color-text-muted)]">
                Kontrollera din e-post för att bekräfta kontot.
              </p>
              <Link href="/login"
                    className="block text-xs text-[var(--color-accent)] hover:underline">
                Gå till inloggning
              </Link>
            </div>
          ) : (
            <>
              <h2 className="text-sm font-semibold mb-5 text-[var(--color-text-primary)]">Registrera dig</h2>
              <form onSubmit={handleRegister} className="space-y-4">
                <div>
                  <label className="text-xs mb-1 block text-[var(--color-text-secondary)]">E-post</label>
                  <input
                    type="email" value={email} onChange={(e) => setEmail(e.target.value)} required
                    className="w-full h-9 px-3 rounded-lg text-sm border bg-[var(--color-bg-elevated)]
                               border-[var(--color-border)] text-[var(--color-text-primary)]
                               focus:border-[var(--color-accent)] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs mb-1 block text-[var(--color-text-secondary)]">Lösenord</label>
                  <input
                    type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                    required minLength={6}
                    className="w-full h-9 px-3 rounded-lg text-sm border bg-[var(--color-bg-elevated)]
                               border-[var(--color-border)] text-[var(--color-text-primary)]
                               focus:border-[var(--color-accent)] focus:outline-none"
                  />
                </div>
                {error && <p className="text-xs text-[var(--color-down)]">{error}</p>}
                <button type="submit" disabled={loading}
                        className="w-full h-9 rounded-lg text-sm font-medium bg-[var(--color-accent)]
                                   text-white hover:bg-[var(--color-accent-hover)] disabled:opacity-50">
                  {loading ? "Skapar konto..." : "Skapa konto"}
                </button>
              </form>
              <p className="mt-4 text-center text-xs text-[var(--color-text-muted)]">
                Har du redan konto?{" "}
                <Link href="/login" className="text-[var(--color-accent)] hover:underline">Logga in</Link>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
