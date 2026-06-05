"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  SlidersHorizontal,
  Briefcase,
  Star,
  Settings,
  TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/oversikt",      icon: LayoutDashboard,    label: "Översikt" },
  { href: "/screener",      icon: SlidersHorizontal,  label: "Screener" },
  { href: "/portfolj",      icon: Briefcase,           label: "Min portfölj" },
  { href: "/bevakningar",   icon: Star,                label: "Bevakningar" },
] as const;

const BOTTOM_ITEMS = [
  { href: "/kontrollpanel", icon: Settings, label: "Kontrollpanel" },
] as const;

export function NavRail() {
  const pathname = usePathname();

  return (
    <nav className="app-nav flex flex-col items-center py-4 gap-1">
      {/* Logo */}
      <Link
        href="/oversikt"
        className="flex items-center justify-center w-10 h-10 rounded-xl mb-4"
        aria-label="MarketScan hem"
      >
        <TrendingUp
          size={22}
          strokeWidth={1.5}
          style={{ color: "var(--color-accent)" }}
        />
      </Link>

      {/* Main nav */}
      <div className="flex flex-col items-center gap-1 flex-1">
        {NAV_ITEMS.map(({ href, icon: Icon, label }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              title={label}
              className={cn(
                "relative flex items-center justify-center w-10 h-10 rounded-xl transition-colors",
                active
                  ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-elevated)]",
              )}
              aria-current={active ? "page" : undefined}
            >
              {active && (
                <span
                  className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r"
                  style={{ background: "var(--color-accent)" }}
                />
              )}
              <Icon size={18} strokeWidth={1.5} />
            </Link>
          );
        })}
      </div>

      {/* Bottom items */}
      <div className="flex flex-col items-center gap-1">
        {BOTTOM_ITEMS.map(({ href, icon: Icon, label }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              title={label}
              className={cn(
                "flex items-center justify-center w-10 h-10 rounded-xl transition-colors",
                active
                  ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-elevated)]",
              )}
              aria-current={active ? "page" : undefined}
            >
              <Icon size={18} strokeWidth={1.5} />
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
