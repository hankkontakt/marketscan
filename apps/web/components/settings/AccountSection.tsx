import { useState } from "react";
import { ShieldAlert, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { SectionCard, SectionTitle } from "./SectionCard";

export function AccountSection() {
  const [confirming, setConfirming] = useState(false);

  function handleDelete() {
    toast.error("Kontoraderingsfunktionen är inte tillgänglig än");
  }

  return (
    <SectionCard>
      <SectionTitle icon={ShieldAlert} title="Konto" />

      <div className="space-y-4">
        <p className="text-xs text-[var(--color-text-muted)]">
          Ta bort ditt konto och all tillhörande data. Denna åtgärd kan inte ångras.
        </p>

        {!confirming ? (
          <button
            onClick={() => setConfirming(true)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            style={{ background: "var(--color-down-soft)", color: "var(--color-down)", border: "1px solid transparent" }}
          >
            <Trash2 size={14} strokeWidth={1.5} />
            Radera konto
          </button>
        ) : (
          <div className="flex items-center gap-2">
            <button
              onClick={handleDelete}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white transition-opacity bg-[var(--color-down)]"
            >
              <Trash2 size={14} strokeWidth={1.5} />
              Bekräfta radering
            </button>
            <button
              onClick={() => setConfirming(false)}
              className="px-4 py-2 rounded-lg text-sm border transition-colors border-[var(--color-border)] text-[var(--color-text-secondary)]"
            >
              Avbryt
            </button>
          </div>
        )}
      </div>
    </SectionCard>
  );
}
