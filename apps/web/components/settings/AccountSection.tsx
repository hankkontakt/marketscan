import { useState, useEffect } from "react";
import { ShieldAlert, Trash2, AlertTriangle, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { api } from "@/lib/api";
import { SectionCard, SectionTitle } from "./SectionCard";

type Step = "idle" | "confirming" | "typing";

export function AccountSection() {
  const [step, setStep] = useState<Step>("idle");
  const [email, setEmail] = useState<string | null>(null);
  const [typedEmail, setTypedEmail] = useState("");
  const [deleting, setDeleting] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => {
      setEmail(data.user?.email ?? null);
    });
  }, []);

  async function handleDelete() {
    if (!email) {
      toast.error("Kunde inte hämta din e-postadress");
      return;
    }
    if (typedEmail !== email) {
      toast.error("E-postadressen matchar inte");
      return;
    }

    setDeleting(true);
    try {
      await api("/api/profile/account", { method: "DELETE" });
      const supabase = createClient();
      await supabase.auth.signOut();
      router.push("/");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Kunde inte ta bort kontot";
      toast.error(message);
      setDeleting(false);
    }
  }

  function handleBack() {
    if (step === "confirming") {
      setStep("idle");
    } else {
      setStep("confirming");
      setTypedEmail("");
    }
  }

  return (
    <SectionCard>
      <SectionTitle icon={ShieldAlert} title="Konto" />

      <div className="space-y-4">
        <p className="text-xs text-[var(--color-text-muted)]">
          Ta bort ditt konto och all tillhörande data. Denna åtgärd kan inte ångras.
        </p>

        {step === "idle" && (
          <button
            onClick={() => setStep("confirming")}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            style={{ background: "var(--color-down-soft)", color: "var(--color-down)", border: "1px solid transparent" }}
          >
            <Trash2 size={14} strokeWidth={1.5} />
            Radera konto
          </button>
        )}

        {step === "confirming" && (
          <div className="space-y-3">
            <div className="flex items-start gap-2 p-3 rounded-lg bg-[var(--color-down-soft)] border border-[var(--color-down)]/20">
              <AlertTriangle size={14} strokeWidth={1.5} className="mt-0.5 shrink-0 text-[var(--color-down)]" />
              <p className="text-xs text-[var(--color-text-secondary)]">
                Är du säker? All data — portfölj, bevakningar, larm och dina sparade analyser — tas bort permanent.
                Skriv din e-postadress för att bekräfta.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setStep("typing")}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white transition-opacity bg-[var(--color-down)]"
              >
                <Trash2 size={14} strokeWidth={1.5} />
                Bekräfta radering
              </button>
              <button
                onClick={handleBack}
                className="px-4 py-2 rounded-lg text-sm border transition-colors border-[var(--color-border)] text-[var(--color-text-secondary)]"
              >
                Avbryt
              </button>
            </div>
          </div>
        )}

        {step === "typing" && (
          <div className="space-y-3">
            <div className="flex items-start gap-2 p-3 rounded-lg bg-[var(--color-down-soft)] border border-[var(--color-down)]/20">
              <AlertTriangle size={14} strokeWidth={1.5} className="mt-0.5 shrink-0 text-[var(--color-down)]" />
              <div className="text-xs text-[var(--color-text-secondary)]">
                <p className="font-medium text-[var(--color-down)] mb-1">Slutgiltig bekräftelse</p>
                <p>Skriv din e-postadress (<strong>{email}</strong>) nedan för att bekräfta borttagning av kontot.</p>
              </div>
            </div>

            <input
              type="email"
              value={typedEmail}
              onChange={(e) => setTypedEmail(e.target.value)}
              placeholder={email ?? "din@epost.se"}
              disabled={deleting}
              className="w-full h-9 px-3 rounded-lg text-sm border focus:outline-none bg-[var(--color-bg-elevated)] border-[var(--color-border)] text-[var(--color-text-primary)]"
            />

            <div className="flex items-center gap-2">
              <button
                onClick={handleDelete}
                disabled={deleting || typedEmail !== email}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-40 transition-opacity bg-[var(--color-down)]"
              >
                {deleting ? (
                  <Loader2 size={14} strokeWidth={1.5} className="animate-spin" />
                ) : (
                  <Trash2 size={14} strokeWidth={1.5} />
                )}
                {deleting ? "Tar bort..." : "Radera mitt konto"}
              </button>
              <button
                onClick={handleBack}
                disabled={deleting}
                className="px-4 py-2 rounded-lg text-sm border transition-colors border-[var(--color-border)] text-[var(--color-text-secondary)] disabled:opacity-40"
              >
                Avbryt
              </button>
            </div>
          </div>
        )}
      </div>
    </SectionCard>
  );
}
