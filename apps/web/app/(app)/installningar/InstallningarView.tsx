"use client";

import { useState, useEffect } from "react";
import { createClient } from "@/lib/supabase/client";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { useTheme } from "@/hooks/useTheme";
import {
  User,
  Palette,
  KeyRound,
  ShieldAlert,
  Sun,
  Moon,
  Monitor,
  Check,
  Loader2,
  Eye,
  EyeOff,
  Trash2,
} from "lucide-react";
import type { Theme } from "@/hooks/useTheme";

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
  const [section, setSection] = useState<SectionId>("profil");

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-12">
      <h1 className="text-xl font-semibold" style={{ color: "var(--color-text-primary)" }}>
        Inställningar
      </h1>

      {/* Section tabs */}
      <div className="flex gap-1 flex-wrap">
        {SECTIONS.map((s) => {
          const Icon = s.icon;
          const active = section === s.id;
          return (
            <button
              key={s.id}
              onClick={() => setSection(s.id)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs transition-colors ${
                active
                  ? "bg-[var(--color-accent)] text-white"
                  : "bg-[var(--color-bg-surface)] text-[var(--color-text-secondary)] border border-[var(--color-border)] hover:border-[var(--color-border-strong)]"
              }`}
            >
              <Icon size={13} strokeWidth={1.5} />
              {s.label}
            </button>
          );
        })}
      </div>

      {section === "profil"   && <ProfileSection />}
      {section === "tema"     && <ThemeSection />}
      {section === "losenord" && <PasswordSection />}
      {section === "konto"    && <AccountSection />}
    </div>
  );
}

// ─── Profil ────────────────────────────────────────────────────────────────────

function ProfileSection() {
  const [email, setEmail] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => {
      setEmail(data.user?.email ?? null);
    });
    // Fetch existing profile
    createClient()
      .from("profiles")
      .select("display_name")
      .then(({ data }) => {
        if (data?.[0]?.display_name) {
          setDisplayName(data[0].display_name);
        }
      });
  }, []);

  async function handleSave() {
    if (!displayName.trim()) {
      toast.error("Visningsnamn kan inte vara tomt");
      return;
    }
    setSaving(true);
    try {
      await api("/api/profile", {
        method: "PUT",
        body: JSON.stringify({ display_name: displayName.trim() }),
      });
      toast.success("Visningsnamn uppdaterat");
    } catch {
      toast.error("Kunde inte spara visningsnamn");
    } finally {
      setSaving(false);
    }
  }

  return (
    <SectionCard>
      <SectionTitle icon={User} title="Profil" />

      <div className="space-y-4">
        {/* Email (read-only) */}
        <div className="space-y-1">
          <label className="text-xs font-medium" style={{ color: "var(--color-text-muted)" }}>
            E-post
          </label>
          <div
            className="flex items-center h-9 px-3 rounded-lg text-sm border"
            style={{
              background: "var(--color-bg-elevated)",
              borderColor: "var(--color-border)",
              color: "var(--color-text-muted)",
            }}
          >
            {email ?? "Laddar..."}
          </div>
          <p className="text-[11px]" style={{ color: "var(--color-text-muted)" }}>
            Din e-postadress kan inte ändras här.
          </p>
        </div>

        {/* Display name */}
        <div className="space-y-1">
          <label
            htmlFor="display-name"
            className="text-xs font-medium"
            style={{ color: "var(--color-text-muted)" }}
          >
            Visningsnamn
          </label>
          <input
            id="display-name"
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Ditt namn"
            className="w-full h-9 px-3 rounded-lg text-sm border focus:outline-none"
            style={{
              background: "var(--color-bg-elevated)",
              borderColor: "var(--color-border)",
              color: "var(--color-text-primary)",
            }}
          />
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-40 transition-opacity"
          style={{ background: "var(--color-accent)" }}
        >
          {saving ? (
            <Loader2 size={14} strokeWidth={1.5} className="animate-spin" />
          ) : (
            <Check size={14} strokeWidth={1.5} />
          )}
          {saving ? "Sparar..." : "Spara"}
        </button>
      </div>
    </SectionCard>
  );
}

// ─── Tema ───────────────────────────────────────────────────────────────────────

const THEME_OPTIONS: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Ljust",  icon: Sun },
  { value: "dark",  label: "Mörkt",  icon: Moon },
  { value: "auto",  label: "Auto",   icon: Monitor },
];

function ThemeSection() {
  const { theme, setTheme, resolved } = useTheme();

  return (
    <SectionCard>
      <SectionTitle icon={Palette} title="Tema" />

      <div className="space-y-4">
        <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
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
                onClick={() => setTheme(opt.value)}
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
                <Icon
                  size={22}
                  strokeWidth={1.5}
                  style={{ color: active ? "var(--color-accent)" : "var(--color-text-muted)" }}
                />
                <span className={active ? "font-medium" : ""}>
                  {opt.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </SectionCard>
  );
}

// ─── Lösenord ──────────────────────────────────────────────────────────────────

function PasswordSection() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  async function handleChangePassword() {
    if (!currentPassword || !newPassword || !confirmPassword) {
      toast.error("Fyll i alla fält");
      return;
    }
    if (newPassword.length < 8) {
      toast.error("Nytt lösenord måste vara minst 8 tecken");
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error("Lösenorden matchar inte");
      return;
    }

    setSaving(true);
    try {
      const supabase = createClient();

      // First re-authenticate by signing in with current password
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email: (await supabase.auth.getUser()).data.user?.email ?? "",
        password: currentPassword,
      });

      if (signInError) {
        toast.error("Nuvarande lösenord är felaktigt");
        setSaving(false);
        return;
      }

      const { error } = await supabase.auth.updateUser({
        password: newPassword,
      });

      if (error) {
        toast.error(error.message);
      } else {
        toast.success("Lösenord uppdaterat");
        setCurrentPassword("");
        setNewPassword("");
        setConfirmPassword("");
      }
    } catch {
      toast.error("Kunde inte uppdatera lösenord");
    } finally {
      setSaving(false);
    }
  }

  function PasswordInput({
    id,
    value,
    onChange,
    placeholder,
  }: {
    id: string;
    value: string;
    onChange: (v: string) => void;
    placeholder: string;
  }) {
    return (
      <div className="relative">
        <input
          id={id}
          type={showPassword ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full h-9 px-3 pr-9 rounded-lg text-sm border focus:outline-none"
          style={{
            background: "var(--color-bg-elevated)",
            borderColor: "var(--color-border)",
            color: "var(--color-text-primary)",
          }}
        />
      </div>
    );
  }

  return (
    <SectionCard>
      <SectionTitle icon={KeyRound} title="Lösenord" />

      <div className="space-y-4">
        <PasswordInput
          id="current-password"
          value={currentPassword}
          onChange={setCurrentPassword}
          placeholder="Nuvarande lösenord"
        />
        <PasswordInput
          id="new-password"
          value={newPassword}
          onChange={setNewPassword}
          placeholder="Nytt lösenord"
        />
        <PasswordInput
          id="confirm-password"
          value={confirmPassword}
          onChange={setConfirmPassword}
          placeholder="Bekräfta nytt lösenord"
        />

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowPassword(!showPassword)}
            className="flex items-center gap-1.5 text-xs transition-colors"
            style={{ color: "var(--color-text-muted)" }}
          >
            {showPassword ? (
              <EyeOff size={13} strokeWidth={1.5} />
            ) : (
              <Eye size={13} strokeWidth={1.5} />
            )}
            {showPassword ? "Dölj" : "Visa"} lösenord
          </button>
        </div>

        <button
          onClick={handleChangePassword}
          disabled={saving}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-40 transition-opacity"
          style={{ background: "var(--color-accent)" }}
        >
          {saving ? (
            <Loader2 size={14} strokeWidth={1.5} className="animate-spin" />
          ) : (
            <KeyRound size={14} strokeWidth={1.5} />
          )}
          {saving ? "Uppdaterar..." : "Ändra lösenord"}
        </button>
      </div>
    </SectionCard>
  );
}

// ─── Konto ─────────────────────────────────────────────────────────────────────

function AccountSection() {
  const [confirming, setConfirming] = useState(false);

  function handleDelete() {
    toast.error("Kontoraderingsfunktionen är inte tillgänglig än");
  }

  return (
    <SectionCard>
      <SectionTitle icon={ShieldAlert} title="Konto" />

      <div className="space-y-4">
        <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
          Ta bort ditt konto och all tillhörande data. Denna åtgärd kan inte ångras.
        </p>

        {!confirming ? (
          <button
            onClick={() => setConfirming(true)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            style={{
              background: "var(--color-down-soft)",
              color: "var(--color-down)",
              border: "1px solid transparent",
            }}
          >
            <Trash2 size={14} strokeWidth={1.5} />
            Radera konto
          </button>
        ) : (
          <div className="flex items-center gap-2">
            <button
              onClick={handleDelete}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white transition-opacity"
              style={{ background: "var(--color-down)" }}
            >
              <Trash2 size={14} strokeWidth={1.5} />
              Bekräfta radering
            </button>
            <button
              onClick={() => setConfirming(false)}
              className="px-4 py-2 rounded-lg text-sm border transition-colors"
              style={{
                borderColor: "var(--color-border)",
                color: "var(--color-text-secondary)",
              }}
            >
              Avbryt
            </button>
          </div>
        )}
      </div>
    </SectionCard>
  );
}

// ─── Hjälpkomponenter ──────────────────────────────────────────────────────────

function SectionCard({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="rounded-xl p-5 border space-y-5"
      style={{
        background: "var(--color-bg-surface)",
        borderColor: "var(--color-border)",
      }}
    >
      {children}
    </div>
  );
}

function SectionTitle({ icon: Icon, title }: { icon: React.ComponentType<{ size?: number; strokeWidth?: number }>; title: string }) {
  return (
    <div className="flex items-center gap-2">
      <Icon size={16} strokeWidth={1.5} style={{ color: "var(--color-accent)" }} />
      <h2 className="text-sm font-semibold" style={{ color: "var(--color-text-primary)" }}>
        {title}
      </h2>
    </div>
  );
}
