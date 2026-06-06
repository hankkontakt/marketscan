"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import {
  LayoutDashboard,
  SlidersHorizontal,
  Briefcase,
  Star,
  Settings,
  TrendingUp,
  TrendingDown,
  Search,
  ArrowRight,
} from "lucide-react";
import { useCommandPalette } from "@/hooks/useCommandPalette";
import { api } from "@/lib/api";
import { formatPctChange, scoreColorClass } from "@/lib/format";

interface SearchResult {
  ticker: string;
  name: string;
  score_total: number | null;
  entry_signal: string | null;
  price: number | null;
  change_pct: number | null;
}

const QUICK_LINKS = [
  { icon: LayoutDashboard, label: "Översikt", href: "/oversikt" },
  { icon: SlidersHorizontal, label: "Aktier — alla", href: "/screener" },
  { icon: SlidersHorizontal, label: "Aktier — Starkt köpläge", href: "/screener?entry_signal=STARK" },
  { icon: SlidersHorizontal, label: "Aktier — Småbolag", href: "/screener?segments=small_cap,micro_cap" },
  { icon: Briefcase, label: "Min portfölj", href: "/portfolj" },
  { icon: Star, label: "Bevakningar", href: "/bevakningar" },
  { icon: Settings, label: "Kontrollpanel", href: "/kontrollpanel" },
] as const;

export function CommandPalette() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const isOpen = useCommandPalette((s) => s.isOpen);
  const close = useCommandPalette((s) => s.close);
  const toggle = useCommandPalette((s) => s.toggle);

  // Global ⌘K / Ctrl+K shortcut
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        toggle();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [toggle]);

  // Search stocks on query change
  useEffect(() => {
    if (!query.trim() || query.length < 2) {
      setResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await api<SearchResult[]>(`/api/stocks?q=${encodeURIComponent(query)}&limit=8`);
        setResults(data);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 200);
    return () => clearTimeout(timer);
  }, [query]);

  const navigate = useCallback((href: string) => {
    close();
    setQuery("");
    router.push(href);
  }, [close, router]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh] bg-[var(--color-bg-overlay)]"
      onClick={() => close()}
    >
      <div
        className="w-full max-w-xl mx-4 rounded-2xl overflow-hidden shadow-2xl bg-[var(--color-bg-surface)]"
        style={{ border: "1px solid var(--color-border-strong)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <Command shouldFilter={false}>
          <div className="flex items-center gap-2 px-4 border-b border-[var(--color-border)]">
            <Search size={16} strokeWidth={1.5}
                    className="text-[var(--color-text-muted)]" />
            <Command.Input
              value={query}
              onValueChange={setQuery}
              placeholder="Sök aktier, eller hoppa till en vy..."
              className="flex-1 h-12 text-sm bg-transparent outline-none
                         placeholder:text-[var(--color-text-muted)]
                         text-[var(--color-text-primary)]"
            />
            <kbd className="text-[10px] px-1.5 py-0.5 rounded font-mono shrink-0
                            bg-[var(--color-bg-elevated)] border border-[var(--color-border)]
                            text-[var(--color-text-muted)]">
              ESC
            </kbd>
          </div>

          <Command.List className="max-h-80 overflow-y-auto py-2">
            {/* Stock search results */}
            {results.length > 0 && (
              <Command.Group heading="Aktier" className="px-2">
                {results.map((stock) => (
                  <Command.Item
                    key={stock.ticker}
                    value={stock.ticker}
                    onSelect={() => navigate(`/aktie/${stock.ticker}`)}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer
                               data-[selected=true]:bg-[var(--color-bg-elevated)]
                               text-[var(--color-text-primary)] text-sm"
                  >
                    <div className="flex flex-col flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-medium">{stock.ticker}</span>
                        <span className="text-[var(--color-text-secondary)] truncate text-xs">
                          {stock.name}
                        </span>
                      </div>
                    </div>
                    {stock.score_total != null && (
                      <span className={`tabular text-xs font-mono font-semibold ${scoreColorClass(stock.score_total)}`}>
                        {Math.round(stock.score_total)}
                      </span>
                    )}
                    {stock.change_pct != null && (
                      <span className={`tabular text-xs font-mono ${stock.change_pct >= 0 ? "text-[var(--color-up)]" : "text-[var(--color-down)]"}`}>
                        {formatPctChange(stock.change_pct)}
                      </span>
                    )}
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            {/* Quick navigation */}
            {!query && (
              <Command.Group heading="Vyer" className="px-2">
                {QUICK_LINKS.map((link) => (
                  <Command.Item
                    key={link.href}
                    value={link.label}
                    onSelect={() => navigate(link.href)}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer
                               data-[selected=true]:bg-[var(--color-bg-elevated)]
                               text-[var(--color-text-secondary)] text-sm"
                  >
                    <link.icon size={15} strokeWidth={1.5}
                               className="text-[var(--color-text-muted)]" />
                    <span>{link.label}</span>
                    <ArrowRight size={13} strokeWidth={1.5}
                                className="ml-auto opacity-40" />
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            {loading && (
              <div className="py-8 text-center text-xs text-[var(--color-text-muted)]">
                Söker...
              </div>
            )}

            {!loading && query.length >= 2 && results.length === 0 && (
              <div className="py-8 text-center text-xs text-[var(--color-text-muted)]">
                Inga aktier matchade &ldquo;{query}&rdquo;
              </div>
            )}
          </Command.List>
        </Command>
      </div>
    </div>
  );
}
