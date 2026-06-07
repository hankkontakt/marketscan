import { Palette, Sun, Moon, Monitor } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import type { Theme } from "@/hooks/useTheme";
import { SectionCard, SectionTitle } from "./SectionCard";
import { api } from "@/lib/api";

const THEME_OPTIONS: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Ljust",  icon: Sun },
  { value: "dark",  label: "Mörkt",  icon: Moon },
  { value: "auto",  label: "Auto",   icon: Monitor },
];

export function ThemeSection() {
  const { theme, setTheme, resolved } = useTheme();

  function handleThemeChange(value: Theme) {
    setTheme(value);
    // Sync to Supabase profile
    api("/api/profile", {
      method: "PUT",
      body: JSON.stringify({ theme: value }),
    }).catch(() => {});
  }

  return (
    <SectionCard>
      <SectionTitle icon={Palette} title="Tema" />

      <div className="space-y-4">
        <p className="text-xs text-[var(--color-text-muted)]">
          {theme === "auto"
            ? `Följer systemets utseende (${resolved === "dark" ? "mörkt" : "ljust"} just nu)`
            : `Välj mellan ljust, mörkt eller automatiskt (följer ditt system)`}
        </p>

        <div className="flex gap-3">
          {THEME_OPTIONS.map((opt) => {
            const Icon = opt.icon;
            const active = theme === opt.value;
            return (
              <button
                key={opt.value}
                onClick={() => handleThemeChange(opt.value)}
                className={`flex flex-col items-center gap-2 px-6 py-4 rounded-xl border text-xs transition-all ${
                  active
                    ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)]"
                    : "border-[var(--color-border)] hover:border-[var(--color-border-strong)]"
                }`}
                style={{
                  background: active ? "var(--color-accent-soft)" : "var(--color-bg-surface)",
                  color: "var(--color-text-primary)",
                }}
              >
                <Icon size={22} strokeWidth={1.5} className={active ? "text-[var(--color-accent)]" : "text-[var(--color-text-muted)]"} />
                <span className={active ? "font-medium" : ""}>{opt.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </SectionCard>
  );
}
