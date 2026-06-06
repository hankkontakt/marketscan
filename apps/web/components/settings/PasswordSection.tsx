import { useState } from "react";
import { KeyRound, Eye, EyeOff, Check, Loader2 } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { toast } from "sonner";
import { SectionCard, SectionTitle } from "./SectionCard";

export function PasswordSection() {
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
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email: (await supabase.auth.getUser()).data.user?.email ?? "",
        password: currentPassword,
      });
      if (signInError) {
        toast.error("Nuvarande lösenord är felaktigt");
        setSaving(false);
        return;
      }
      const { error } = await supabase.auth.updateUser({ password: newPassword });
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

  function PasswordInput({ id, value, onChange, placeholder }: {
    id: string; value: string; onChange: (v: string) => void; placeholder: string;
  }) {
    return (
      <div className="relative">
        <input
          id={id}
          type={showPassword ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full h-9 px-3 pr-9 rounded-lg text-sm border focus:outline-none bg-[var(--color-bg-elevated)] border-[var(--color-border)] text-[var(--color-text-primary)]"
        />
      </div>
    );
  }

  return (
    <SectionCard>
      <SectionTitle icon={KeyRound} title="Lösenord" />

      <div className="space-y-4">
        <PasswordInput id="current-password" value={currentPassword} onChange={setCurrentPassword} placeholder="Nuvarande lösenord" />
        <PasswordInput id="new-password" value={newPassword} onChange={setNewPassword} placeholder="Nytt lösenord" />
        <PasswordInput id="confirm-password" value={confirmPassword} onChange={setConfirmPassword} placeholder="Bekräfta nytt lösenord" />

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowPassword(!showPassword)}
            className="flex items-center gap-1.5 text-xs transition-colors text-[var(--color-text-muted)]"
          >
            {showPassword ? <EyeOff size={13} strokeWidth={1.5} /> : <Eye size={13} strokeWidth={1.5} />}
            {showPassword ? "Dölj" : "Visa"} lösenord
          </button>
        </div>

        <button
          onClick={handleChangePassword}
          disabled={saving}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-40 transition-opacity bg-[var(--color-accent)]"
        >
          {saving ? <Loader2 size={14} strokeWidth={1.5} className="animate-spin" /> : <KeyRound size={14} strokeWidth={1.5} />}
          {saving ? "Uppdaterar..." : "Ändra lösenord"}
        </button>
      </div>
    </SectionCard>
  );
}
