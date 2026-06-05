"use client";

import { Search, Moon, Sun, User } from "lucide-react";
import { useCommandPalette } from "@/hooks/useCommandPalette";
import { useTheme } from "@/hooks/useTheme";

export function TopBar() {
  const { open } = useCommandPalette();
  const { theme, toggle } = useTheme();

  return (
    <header className="app-topbar flex items-center gap-3 px-6">
      {/* Global search — triggers ⌘K palette */}
      <button
        onClick={open}
        className="flex items-center gap-2 flex-1 max-w-96 h-8 px-3 rounded-lg text-sm
                   border transition-colors cursor-pointer
                   bg-[var(--color-bg-elevated)] border-[var(--color-border)]
                   text-[var(--color-text-muted)] hover:border-[var(--color-border-strong)]"
        aria-label="Sök (⌘K)"
      >
        <Search size={14} strokeWidth={1.5} />
        <span className="text-xs">Sök aktier, vyer... </span>
        <kbd className="ml-auto text-[10px] px-1.5 py-0.5 rounded
                        bg-[var(--color-bg-surface)] border border-[var(--color-border)]
                        font-mono text-[var(--color-text-muted)]">
          ⌘K
        </kbd>
      </button>

      <div className="flex-1" />

      {/* Theme toggle */}
      <button
        onClick={toggle}
        className="flex items-center justify-center w-8 h-8 rounded-lg transition-colors
                   text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]
                   hover:bg-[var(--color-bg-elevated)]"
        aria-label={`Byt till ${theme === "dark" ? "ljust" : "mörkt"} tema`}
      >
        {theme === "dark"
          ? <Sun size={16} strokeWidth={1.5} />
          : <Moon size={16} strokeWidth={1.5} />}
      </button>

      {/* User menu placeholder */}
      <button
        className="flex items-center justify-center w-8 h-8 rounded-full
                   border border-[var(--color-border)] text-[var(--color-text-muted)]
                   hover:border-[var(--color-border-strong)] transition-colors"
        aria-label="Konto"
      >
        <User size={15} strokeWidth={1.5} />
      </button>
    </header>
  );
}
