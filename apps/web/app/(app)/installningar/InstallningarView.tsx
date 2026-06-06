"use client";

import * as Tabs from "@radix-ui/react-tabs";
import { User, Palette, KeyRound, ShieldAlert } from "lucide-react";
import { ProfileSection } from "@/components/settings/ProfileSection";
import { ThemeSection } from "@/components/settings/ThemeSection";
import { PasswordSection } from "@/components/settings/PasswordSection";
import { AccountSection } from "@/components/settings/AccountSection";

// ─── Sektioner ─────────────────────────────────────────────────────────────────

const SECTIONS = [
  { id: "profil",    icon: User,       label: "Profil" },
  { id: "tema",      icon: Palette,    label: "Tema" },
  { id: "losenord",  icon: KeyRound,   label: "Lösenord" },
  { id: "konto",     icon: ShieldAlert, label: "Konto" },
] as const;

type SectionId = (typeof SECTIONS)[number]["id"];

// ─── Huvudvy ───────────────────────────────────────────────────────────────────

export function InstallningarView() {
  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-12">
      <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">
        Inställningar
      </h1>

      <Tabs.Root defaultValue="profil">
        {/* Section tabs */}
        <Tabs.List className="flex gap-1 flex-wrap">
          {SECTIONS.map((s) => {
            const Icon = s.icon;
            return (
              <Tabs.Trigger
                key={s.id}
                value={s.id}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs transition-colors
                           data-[state=active]:bg-[var(--color-accent)] data-[state=active]:text-white
                           data-[state=inactive]:bg-[var(--color-bg-surface)] data-[state=inactive]:text-[var(--color-text-secondary)]
                           data-[state=inactive]:border data-[state=inactive]:border-[var(--color-border)]
                           data-[state=inactive]:hover:border-[var(--color-border-strong)]"
              >
                <Icon size={13} strokeWidth={1.5} />
                {s.label}
              </Tabs.Trigger>
            );
          })}
        </Tabs.List>

        <Tabs.Content value="profil"><ProfileSection /></Tabs.Content>
        <Tabs.Content value="tema"><ThemeSection /></Tabs.Content>
        <Tabs.Content value="losenord"><PasswordSection /></Tabs.Content>
        <Tabs.Content value="konto"><AccountSection /></Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
