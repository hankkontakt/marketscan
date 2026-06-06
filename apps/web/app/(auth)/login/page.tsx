"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { TrendingUp } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();
  const supabase = createClient();

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      setError(error.message);
      setLoading(false);
    } else {
      router.push("/oversikt");
      router.refresh();
    }
  }

  return (
    <div className="min-h-dvh flex items-center justify-center p-4 bg-[var(--color-bg-base)]">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center mb-3 bg-[var(--color-accent-soft)]" style={{ border: "1px solid var(--color-border)" }}>
            <TrendingUp size={22} strokeWidth={1.5} className="text-[var(--color-accent)]" />
          </div>
          <h1 className="text-xl font-bold text-[var(--color-text-primary)]">MarketScan</h1>
          <p className="text-xs mt-1 text-[var(--color-text-muted)]">Professionell aktieanalys</p>
        </div>

        {/* Form */}
        <div className="rounded-2xl p-6 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
          <h2 className="text-sm font-semibold mb-5 text-[var(--color-text-primary)]">Logga in</h2>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="text-xs mb-1 block text-[var(--color-text-secondary)]">
                E-post
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full h-9 px-3 rounded-lg text-sm border
                           bg-[var(--color-bg-elevated)] border-[var(--color-border)]
                           text-[var(--color-text-primary)]
                           focus:border-[var(--color-accent)] focus:outline-none"
              />
            </div>
            <div>
              <label className="text-xs mb-1 block text-[var(--color-text-secondary)]">
                Lösenord
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full h-9 px-3 rounded-lg text-sm border
                           bg-[var(--color-bg-elevated)] border-[var(--color-border)]
                           text-[var(--color-text-primary)]
                           focus:border-[var(--color-accent)] focus:outline-none"
              />
            </div>

            {error && (
              <p className="text-xs text-[var(--color-down)] px-1">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full h-9 rounded-lg text-sm font-medium transition-colors
                         bg-[var(--color-accent)] text-white
                         hover:bg-[var(--color-accent-hover)]
                         disabled:opacity-50"
            >
              {loading ? "Loggar in..." : "Logga in"}
            </button>
          </form>
          <p className="mt-4 text-center text-xs text-[var(--color-text-muted)]">
            Inget konto?{" "}
            <Link href="/register" className="hover:underline text-[var(--color-accent)]">
              Skapa ett gratis konto
            </Link>
          </p>
          <p className="mt-1 text-center text-xs">
            <Link href="/reset" className="hover:underline text-[var(--color-text-muted)]">
              Glömt lösenordet?
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
