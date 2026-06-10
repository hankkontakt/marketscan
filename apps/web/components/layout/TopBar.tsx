"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Search, Moon, Sun, User, LogOut, Settings, ChevronDown, TrendingUp,
  Briefcase, SlidersHorizontal, Globe, Star, CalendarDays, BarChart2,
  BookOpen, Shield, FlaskConical, Activity, Brain, Eye, ArrowLeftRight,
  Menu, X, Compass,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useCommandPalette } from "@/hooks/useCommandPalette";
import { useTheme } from "@/hooks/useTheme";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import { NotificationBell } from "@/components/notifications/NotificationCenter";
import { useScanMeta } from "@/hooks/useScreener";
import { useExperience, type ExperienceLevel } from "@/components/providers/ExperienceProvider";

// ── Nav data ───────────────────────────────────────────────────────────────

/** Primary links visible inline in the topbar */
const PRIMARY_NAV = [
  { href: "/daglig-briefing", label: "Hem" },
  { href: "/portfolj",        label: "Portfölj" },
  { href: "/screener",        label: "Aktier" },
  { href: "/marknad",         label: "Marknad" },
  { href: "/bevakningar",     label: "Bevakningar" },
  { href: "/kalender",        label: "Kalender" },
] as const;

/** Verktyg dropdown items (desktop) */
const VERKTYG_ITEMS = [
  { href: "/jamfor",           label: "Jämför aktier",  icon: ArrowLeftRight, desc: "Analysera aktier sida vid sida" },
  { href: "/insider-radar",    label: "Insider Radar",   icon: Eye,            desc: "Insiderhandel och stora affärer" },
  { href: "/signal-analytics", label: "Signalanalys",    icon: Activity,       desc: "Validera och backtesta signaler" },
  { href: "/strategi-lab",     label: "Strategi Lab",    icon: FlaskConical,   desc: "Bygg och optimera egna strategier" },
] as const;

/** Full list with icons for the mobile drawer */
const DRAWER_PRIMARY = [
  { href: "/daglig-briefing", label: "Hem",         icon: BarChart2 },
  { href: "/portfolj",        label: "Portfölj",    icon: Briefcase },
  { href: "/screener",        label: "Aktier",      icon: SlidersHorizontal },
  { href: "/marknad",         label: "Marknad",     icon: Globe },
  { href: "/bevakningar",     label: "Bevakningar", icon: Star },
  { href: "/kalender",        label: "Kalender",    icon: CalendarDays },
  { href: "/guide",           label: "Guide",       icon: BookOpen },
] as const;

const DRAWER_VERKTYG = [
  { href: "/jamfor",           label: "Jämför aktier", icon: ArrowLeftRight },
  { href: "/insider-radar",    label: "Insider Radar",  icon: Eye },
  { href: "/signal-analytics", label: "Signalanalys",   icon: Activity },
  { href: "/strategi-lab",     label: "Strategi Lab",   icon: FlaskConical },
] as const;

/** Map each experience level to its primary nav links */
const NAV_BY_LEVEL: Record<ExperienceLevel, readonly { href: string; label: string }[]> = {
  beginner: [
    { href: "/daglig-briefing", label: "Hem" },
    { href: "/upptack",        label: "Upptäck" },
    { href: "/bevakningar",     label: "Bevakningar" },
    { href: "/guide",           label: "Guide" },
    { href: "/installningar",   label: "Inställningar" },
  ],
  intermediate: [
    { href: "/daglig-briefing", label: "Hem" },
    { href: "/upptack",        label: "Upptäck" },
    { href: "/portfolj",        label: "Portfölj" },
    { href: "/bevakningar",     label: "Bevakningar" },
    { href: "/kalender",        label: "Kalender" },
    { href: "/installningar",   label: "Inställningar" },
  ],
  expert: PRIMARY_NAV as unknown as readonly { href: string; label: string }[],
};

/** Map each experience level to its drawer primary items */
const DRAWER_BY_LEVEL: Record<ExperienceLevel, readonly { href: string; label: string; icon: any }[]> = {
  beginner: [
    { href: "/daglig-briefing", label: "Hem",         icon: BarChart2 },
    { href: "/upptack",        label: "Upptäck",     icon: Compass },
    { href: "/bevakningar",     label: "Bevakningar", icon: Star },
    { href: "/guide",           label: "Guide",       icon: BookOpen },
  ],
  intermediate: [
    { href: "/daglig-briefing", label: "Hem",         icon: BarChart2 },
    { href: "/upptack",        label: "Upptäck",     icon: Compass },
    { href: "/portfolj",        label: "Portfölj",    icon: Briefcase },
    { href: "/bevakningar",     label: "Bevakningar", icon: Star },
    { href: "/kalender",        label: "Kalender",    icon: CalendarDays },
  ],
  expert: DRAWER_PRIMARY as unknown as readonly { href: string; label: string; icon: any }[],
};

// ── Component ──────────────────────────────────────────────────────────────

export function TopBar() {
  const openPalette   = useCommandPalette((s) => s.open);
  const { resolved, toggle } = useTheme();
  const { level } = useExperience();
  const [userMenuOpen,  setUserMenuOpen]  = useState(false);
  const [drawerOpen,    setDrawerOpen]    = useState(false);
  const [verktygOpen,   setVerktygOpen]   = useState(false);
  const [userEmail,     setUserEmail]     = useState<string | null>(null);
  const [isAdmin,       setIsAdmin]       = useState(false);
  const menuRef    = useRef<HTMLDivElement>(null);
  const verktygRef = useRef<HTMLDivElement>(null);
  const router     = useRouter();
  const pathname   = usePathname();
  const { data: scanMeta } = useScanMeta();

  // Resolve nav items for current level
  const currentNav = NAV_BY_LEVEL[level];
  const currentDrawer = DRAWER_BY_LEVEL[level];
  const showVerktyg = level === "expert";

  // Fetch user + admin status
  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => {
      setUserEmail(data.user?.email ?? null);
    });
    supabase.auth.getSession().then(({ data }) => {
      const token = data.session?.access_token;
      if (!token) return;
      try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        const role: string =
          (payload.app_metadata?.role as string | undefined) ??
          (payload.user_metadata?.role as string | undefined) ?? "";
        if (role === "admin") setIsAdmin(true);
      } catch { /* ignore */ }
    });
  }, []);

  // Close dropdowns on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (menuRef.current    && !menuRef.current.contains(e.target as Node))    setUserMenuOpen(false);
      if (verktygRef.current && !verktygRef.current.contains(e.target as Node)) setVerktygOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Close drawer on navigation
  useEffect(() => { setDrawerOpen(false); }, [pathname]);

  async function handleLogout() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
  }

  const isVerktygActive = VERKTYG_ITEMS.some(i => pathname.startsWith(i.href));

  return (
    <>
      {/* ═══════════════════════════════════════════════════════════════
          Top bar
      ═══════════════════════════════════════════════════════════════ */}
      <header className="app-topbar flex items-center gap-1 px-4 lg:px-6">

        {/* Logo */}
        <Link
          href="/daglig-briefing"
          className="flex items-center gap-2 mr-3 shrink-0"
          aria-label="MarketScan — till startsidan"
        >
          <TrendingUp size={19} strokeWidth={1.5} className="text-[var(--color-accent)]" />
          <span className="font-semibold text-sm text-[var(--color-text-primary)] hidden sm:block tracking-tight">
            MarketScan
          </span>
        </Link>

        {/* ── Primary nav links (desktop only) ────────────────────── */}
        <nav className="hidden lg:flex items-center gap-0.5 flex-1" aria-label="Huvudnavigation">
          {currentNav.map(({ href, label }) => {
            const active = pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                  active
                    ? "text-[var(--color-accent)] bg-[var(--color-accent-soft)]"
                    : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)]",
                )}
                aria-current={active ? "page" : undefined}
              >
                {label}
              </Link>
            );
          })}

          {/* Verktyg dropdown — expert only */}
          {showVerktyg && (
            <div className="relative" ref={verktygRef}>
              <button
                onClick={() => setVerktygOpen(!verktygOpen)}
                aria-expanded={verktygOpen}
                className={cn(
                  "flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                  isVerktygActive
                    ? "text-[var(--color-accent)] bg-[var(--color-accent-soft)]"
                    : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)]",
                )}
              >
                Verktyg
                <ChevronDown
                  size={13}
                  strokeWidth={1.5}
                  className={cn("transition-transform duration-200", verktygOpen && "rotate-180")}
                />
              </button>

              {verktygOpen && (
                <div className="absolute top-[calc(100%+6px)] left-0 w-64 rounded-xl border shadow-xl z-50
                                overflow-hidden bg-[var(--color-bg-surface)] border-[var(--color-border-strong)]">
                  {VERKTYG_ITEMS.map(({ href, label, icon: Icon, desc }) => {
                    const active = pathname.startsWith(href);
                    return (
                      <Link
                        key={href}
                        href={href}
                        onClick={() => setVerktygOpen(false)}
                        className={cn(
                          "flex items-start gap-3 px-4 py-3 transition-colors",
                          active ? "bg-[var(--color-accent-soft)]" : "hover:bg-[var(--color-bg-elevated)]",
                        )}
                      >
                        <Icon
                          size={15}
                          strokeWidth={1.5}
                          className={cn(
                            "mt-0.5 shrink-0",
                            active ? "text-[var(--color-accent)]" : "text-[var(--color-text-muted)]",
                          )}
                        />
                        <div>
                          <p className={cn(
                            "text-sm font-medium",
                            active ? "text-[var(--color-accent)]" : "text-[var(--color-text-primary)]",
                          )}>
                            {label}
                          </p>
                          <p className="text-xs text-[var(--color-text-muted)] mt-0.5 leading-tight">{desc}</p>
                        </div>
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </nav>

        {/* Spacer on mobile */}
        <div className="flex-1 lg:hidden" />

        {/* ── Right-side actions ───────────────────────────────────── */}

        {/* Search */}
        <button
          onClick={openPalette}
          className="hidden sm:flex items-center gap-2 h-8 px-3 rounded-lg text-xs border transition-colors
                     bg-[var(--color-bg-elevated)] border-[var(--color-border)]
                     text-[var(--color-text-muted)] hover:border-[var(--color-border-strong)]"
          aria-label="Sök aktier"
        >
          <Search size={13} strokeWidth={1.5} />
          <span className="hidden md:block">Sök aktier…</span>
          <kbd className="hidden lg:block text-[10px] opacity-40 font-mono ml-1">⌘K</kbd>
        </button>

        {/* Scan date */}
        {scanMeta?.scan_date && (
          <span className="text-[11px] text-[var(--color-text-muted)] hidden xl:block px-2">
            {new Date(scanMeta.scan_date).toLocaleDateString("sv-SE")}
          </span>
        )}

        {/* Notification bell */}
        <NotificationBell />

        {/* Theme toggle */}
        <button
          onClick={toggle}
          className="flex items-center justify-center w-8 h-8 rounded-lg transition-colors
                     text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]
                     hover:bg-[var(--color-bg-elevated)]"
          aria-label={`Byt till ${resolved === "dark" ? "ljust" : "mörkt"} tema`}
        >
          {resolved === "dark"
            ? <Sun  size={15} strokeWidth={1.5} />
            : <Moon size={15} strokeWidth={1.5} />}
        </button>

        {/* User menu — hidden on mobile (accessible via drawer) */}
        <div className="relative hidden sm:block" ref={menuRef}>
          <button
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            className="flex items-center gap-1.5 h-8 px-2.5 rounded-lg transition-colors border
                       border-[var(--color-border)] text-[var(--color-text-muted)]
                       hover:border-[var(--color-border-strong)] hover:text-[var(--color-text-secondary)]"
            aria-label="Kontomeny"
            aria-expanded={userMenuOpen}
          >
            <User size={14} strokeWidth={1.5} />
            {userEmail && (
              <span className="text-xs hidden md:block max-w-28 truncate">
                {userEmail.split("@")[0]}
              </span>
            )}
            <ChevronDown size={12} strokeWidth={1.5} />
          </button>

          {userMenuOpen && (
            <div className="absolute right-0 top-[calc(100%+6px)] w-56 rounded-xl border shadow-xl z-50
                            overflow-hidden bg-[var(--color-bg-surface)] border-[var(--color-border-strong)]">
              {/* Account info */}
              <div className="px-4 py-3 border-b border-[var(--color-border)]">
                {userEmail ? (
                  <>
                    <p className="text-xs text-[var(--color-text-muted)]">Inloggad som</p>
                    <p className="text-sm font-medium text-[var(--color-text-primary)] truncate mt-0.5">{userEmail}</p>
                  </>
                ) : (
                  <>
                    <p className="text-xs text-[var(--color-text-muted)]">Inte inloggad</p>
                    <a href="/login" className="text-sm text-[var(--color-accent)] hover:underline mt-0.5 block">Logga in</a>
                  </>
                )}
              </div>

              {/* Menu links */}
              <div className="py-1">
                <a href="/installningar" className="flex items-center gap-2.5 px-4 py-2.5 text-sm transition-colors
                                                    text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]
                                                    hover:bg-[var(--color-bg-elevated)]">
                  <Settings size={14} strokeWidth={1.5} />
                  Inställningar
                </a>
                <a href="/guide" className="flex items-center gap-2.5 px-4 py-2.5 text-sm transition-colors
                                            text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]
                                            hover:bg-[var(--color-bg-elevated)]">
                  <BookOpen size={14} strokeWidth={1.5} />
                  Guide
                </a>

                {/* Admin links */}
                {isAdmin && (
                  <>
                    <div className="h-px mx-4 my-1 bg-[var(--color-border)]" />
                    <a href="/kontrollpanel" className="flex items-center gap-2.5 px-4 py-2.5 text-sm transition-colors
                                                        text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]
                                                        hover:bg-[var(--color-bg-elevated)]">
                      <Shield size={14} strokeWidth={1.5} />
                      Kontrollpanel
                    </a>
                    <a href="/ai-prestanda" className="flex items-center gap-2.5 px-4 py-2.5 text-sm transition-colors
                                                       text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]
                                                       hover:bg-[var(--color-bg-elevated)]">
                      <Brain size={14} strokeWidth={1.5} />
                      AI-prestanda
                    </a>
                  </>
                )}

                {userEmail && (
                  <>
                    <div className="h-px mx-4 my-1 bg-[var(--color-border)]" />
                    <button
                      onClick={handleLogout}
                      className="flex items-center gap-2.5 px-4 py-2.5 text-sm w-full text-left transition-colors
                                 text-[var(--color-down)] hover:bg-[var(--color-bg-elevated)]"
                    >
                      <LogOut size={14} strokeWidth={1.5} />
                      Logga ut
                    </button>
                  </>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Hamburger — mobile / small screens */}
        <button
          onClick={() => setDrawerOpen(true)}
          className="flex items-center justify-center w-8 h-8 rounded-lg transition-colors
                     text-[var(--color-text-muted)] hover:bg-[var(--color-bg-elevated)] lg:hidden"
          aria-label="Öppna meny"
        >
          <Menu size={18} strokeWidth={1.5} />
        </button>
      </header>

      {/* ═══════════════════════════════════════════════════════════════
          Mobile nav drawer
      ═══════════════════════════════════════════════════════════════ */}

      {/* Backdrop */}
      {drawerOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/30 backdrop-blur-[2px] lg:hidden"
          onClick={() => setDrawerOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Drawer panel */}
      <aside
        aria-label="Mobilnavigation"
        className={cn(
          "fixed top-0 left-0 h-full w-72 z-50 flex flex-col lg:hidden",
          "bg-[var(--color-bg-surface)] border-r border-[var(--color-border)] shadow-2xl",
          "transition-transform duration-300 ease-in-out",
          drawerOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {/* Drawer header */}
        <div className="flex items-center justify-between px-5 h-[var(--topbar-height)] border-b border-[var(--color-border)] shrink-0">
          <div className="flex items-center gap-2">
            <TrendingUp size={18} strokeWidth={1.5} className="text-[var(--color-accent)]" />
            <span className="font-semibold text-sm text-[var(--color-text-primary)]">MarketScan</span>
          </div>
          <button
            onClick={() => setDrawerOpen(false)}
            className="flex items-center justify-center w-7 h-7 rounded-lg
                       text-[var(--color-text-muted)] hover:bg-[var(--color-bg-elevated)]"
            aria-label="Stäng meny"
          >
            <X size={16} strokeWidth={1.5} />
          </button>
        </div>

        {/* Drawer nav */}
        <nav className="flex-1 overflow-y-auto py-3 px-3">
          {/* Primary — level-aware */}
          <div className="space-y-0.5">
            {currentDrawer.map(({ href, label, icon: Icon }) => {
              const active = pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors",
                    active
                      ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                      : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)]",
                  )}
                  aria-current={active ? "page" : undefined}
                >
                  <Icon size={16} strokeWidth={1.5} className="shrink-0" />
                  {label}
                </Link>
              );
            })}
          </div>

          {/* Verktyg section — expert only */}
          {showVerktyg && (
            <div className="mt-5">
              <p className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                Verktyg
              </p>
              <div className="space-y-0.5">
                {DRAWER_VERKTYG.map(({ href, label, icon: Icon }) => {
                  const active = pathname.startsWith(href);
                  return (
                    <Link
                      key={href}
                      href={href}
                      className={cn(
                        "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors",
                        active
                          ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                          : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)]",
                      )}
                      aria-current={active ? "page" : undefined}
                    >
                      <Icon size={16} strokeWidth={1.5} className="shrink-0" />
                      {label}
                    </Link>
                  );
                })}
              </div>
            </div>
          )}

          {/* Admin section */}
          {isAdmin && (
            <div className="mt-5">
              <p className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                Admin
              </p>
              <div className="space-y-0.5">
                {[
                  { href: "/kontrollpanel", label: "Kontrollpanel", icon: Shield },
                  { href: "/ai-prestanda",  label: "AI-prestanda",  icon: Brain  },
                ].map(({ href, label, icon: Icon }) => {
                  const active = pathname.startsWith(href);
                  return (
                    <Link
                      key={href}
                      href={href}
                      className={cn(
                        "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors",
                        active
                          ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                          : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)]",
                      )}
                    >
                      <Icon size={16} strokeWidth={1.5} className="shrink-0" />
                      {label}
                    </Link>
                  );
                })}
              </div>
            </div>
          )}
        </nav>

        {/* Drawer footer */}
        <div className="border-t border-[var(--color-border)] px-3 py-3 space-y-0.5 shrink-0">
          {userEmail && (
            <p className="px-3 py-1.5 text-xs text-[var(--color-text-muted)] truncate">{userEmail}</p>
          )}
          <a
            href="/installningar"
            className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors
                       text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)]"
          >
            <Settings size={16} strokeWidth={1.5} />
            Inställningar
          </a>
          {userEmail && (
            <button
              onClick={handleLogout}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium w-full text-left transition-colors
                         text-[var(--color-down)] hover:bg-[var(--color-bg-elevated)]"
            >
              <LogOut size={16} strokeWidth={1.5} />
              Logga ut
            </button>
          )}
        </div>
      </aside>
    </>
  );
}
