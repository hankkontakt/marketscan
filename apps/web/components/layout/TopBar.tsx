"use client";

import { useState, useRef, useEffect } from "react";
import { Search, Moon, Sun, User, LogOut, Settings, ChevronDown } from "lucide-react";
import { useCommandPalette } from "@/hooks/useCommandPalette";
import { useTheme } from "@/hooks/useTheme";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";

export function TopBar() {
  const open = useCommandPalette((s) => s.open);
  const { resolved, toggle } = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Fetch current user on mount
  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => {
      setUserEmail(data.user?.email ?? null);
    });
  }, []);

  // Close menu on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  async function handleLogout() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
  }

  return (
    <header className="app-topbar flex items-center gap-3 px-6">
      {/* Global search — triggers command palette */}
      <button
        onClick={open}
        className="flex items-center gap-2 flex-1 max-w-sm h-9 px-3 rounded-lg text-sm
                   border transition-colors cursor-pointer
                   bg-[var(--color-bg-elevated)] border-[var(--color-border)]
                   text-[var(--color-text-muted)] hover:border-[var(--color-border-strong)]"
        aria-label="Sök"
      >
        <Search size={14} strokeWidth={1.5} />
        <span className="text-xs text-[var(--color-text-muted)]">Sök aktier eller bolagsnamn</span>
      </button>

      <div className="flex-1" />

      {/* Theme toggle */}
      <button
        onClick={toggle}
        className="flex items-center justify-center w-8 h-8 rounded-lg transition-colors
                   text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]
                   hover:bg-[var(--color-bg-elevated)]"
        aria-label={`Byt till ${resolved === "dark" ? "ljust" : "mörkt"} tema`}
      >
        {resolved === "dark"
          ? <Sun size={16} strokeWidth={1.5} />
          : <Moon size={16} strokeWidth={1.5} />}
      </button>

      {/* User menu */}
      <div className="relative" ref={menuRef}>
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="flex items-center gap-1.5 h-8 px-2.5 rounded-lg transition-colors
                     border border-[var(--color-border)] text-[var(--color-text-muted)]
                     hover:border-[var(--color-border-strong)] hover:text-[var(--color-text-secondary)]"
          aria-label="Kontomeny"
        >
          <User size={14} strokeWidth={1.5} />
          {userEmail && (
            <span className="text-xs hidden sm:block max-w-32 truncate">
              {userEmail.split("@")[0]}
            </span>
          )}
          <ChevronDown size={12} strokeWidth={1.5} />
        </button>

        {menuOpen && (
          <div
            className="absolute right-0 top-10 w-56 rounded-xl border shadow-xl z-50 overflow-hidden bg-[var(--color-bg-elevated)] border-[var(--color-border-strong)]"
          >
            {/* User info */}
            {userEmail && (
              <div
                className="px-4 py-3 border-b border-[var(--color-border)]"
              >
                <p className="text-xs text-[var(--color-text-muted)]">Inloggad som</p>
                <p className="text-sm font-medium text-[var(--color-text-primary)] truncate mt-0.5">
                  {userEmail}
                </p>
              </div>
            )}

            {!userEmail && (
              <div className="px-4 py-3 border-b border-[var(--color-border)]">
                <p className="text-xs text-[var(--color-text-muted)]">Inte inloggad</p>
                <a
                  href="/login"
                  className="text-sm text-[var(--color-accent)] hover:underline mt-0.5 block"
                >
                  Logga in
                </a>
              </div>
            )}

            {/* Menu items */}
            <div className="py-1">
              <a
                href="/installningar"
                className="flex items-center gap-2.5 px-4 py-2.5 text-sm transition-colors
                           text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]
                           hover:bg-[var(--color-bg-surface)]"
              >
                <Settings size={14} strokeWidth={1.5} />
                Inställningar
              </a>

              {userEmail && (
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2.5 px-4 py-2.5 text-sm w-full text-left transition-colors
                             text-[var(--color-down)] hover:bg-[var(--color-bg-surface)]"
                >
                  <LogOut size={14} strokeWidth={1.5} />
                  Logga ut
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
