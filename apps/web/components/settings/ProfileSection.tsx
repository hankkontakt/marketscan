import { useState, useEffect } from "react";
import { User, Check, Loader2 } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { SectionCard, SectionTitle } from "./SectionCard";

export function ProfileSection() {
  const [email, setEmail] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => {
      setEmail(data.user?.email ?? null);
    });
    api<{ display_name: string | null }>("/api/profile").then((data) => {
      if (data.display_name) {
        setDisplayName(data.display_name);
      }
    }).catch(() => {});
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
        <div className="space-y-1">
          <label className="text-xs font-medium text-[var(--color-text-muted)]">E-post</label>
          <div className="flex items-center h-9 px-3 rounded-lg text-sm border bg-[var(--color-bg-elevated)] border-[var(--color-border)] text-[var(--color-text-muted)]">
            {email ?? "Laddar..."}
          </div>
          <p className="text-[11px] text-[var(--color-text-muted)]">
            Din e-postadress kan inte ändras här.
          </p>
        </div>

        <div className="space-y-1">
          <label htmlFor="display-name" className="text-xs font-medium text-[var(--color-text-muted)]">Visningsnamn</label>
          <input
            id="display-name"
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Ditt namn"
            className="w-full h-9 px-3 rounded-lg text-sm border focus:outline-none bg-[var(--color-bg-elevated)] border-[var(--color-border)] text-[var(--color-text-primary)]"
          />
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-40 transition-opacity bg-[var(--color-accent)]"
        >
          {saving ? <Loader2 size={14} strokeWidth={1.5} className="animate-spin" /> : <Check size={14} strokeWidth={1.5} />}
          {saving ? "Sparar..." : "Spara"}
        </button>
      </div>
    </SectionCard>
  );
}
