"use client";

import { useState } from "react";
import { Upload, X, Check, Loader2, AlertCircle, FileUp } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface ImportPreviewItem {
  name: string;
  ticker: string | null;
  shares: number | null;
  cost_basis: number | null;
  current_price: number | null;
  mapped: boolean;
}

interface Props {
  onClose: () => void;
}

export function ImportModal({ onClose }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreviewItem[] | null>(null);
  const [overrides, setOverrides] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);

  async function handleUpload() {
    if (!file) return;
    setLoading(true);
    try {
      // Read CSV client-side and send as JSON
      const text = await file.text();
      const rows = text.split("\n").filter(Boolean).map((line) => ({ raw: line }));
      const data = await api<{ rows: ImportPreviewItem[]; mapped_count: number; unmapped_count: number; total: number }>(
        "/api/portfolio/import/preview",
        {
          method: "POST",
          body: JSON.stringify({ rows }),
        },
      );
      setPreview(data.rows);
    } catch (err: any) {
      toast.error(err.message || "Kunde inte ladda CSV");
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm() {
    if (!preview) return;
    setConfirming(true);
    try {
      const resolved = preview.map((r, i) => ({
        ...r,
        ticker: overrides[i]?.toUpperCase() || r.ticker,
      }));
      await api("/api/portfolio/import/confirm", {
        method: "POST",
        body: JSON.stringify({ rows: resolved }),
      });
      toast.success(`${resolved.filter((r) => r.ticker && r.shares).length} innehav importerade`);
      onClose();
      window.location.reload();
    } catch (err: any) {
      toast.error(err.message || "Kunde inte bekräfta import");
    } finally {
      setConfirming(false);
    }
  }

  const mappedCount = preview?.filter((r) => r.ticker && overrides[preview.indexOf(r)] == null)?.length ?? 0;
  const totalWithTicker = preview?.filter((r) => r.ticker || overrides[preview.indexOf(r)]).length ?? 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl shadow-2xl bg-[var(--color-bg-surface)] border border-[var(--color-border-strong)]"
           style={{ maxHeight: "80vh" }}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--color-border)]">
          <div className="flex items-center gap-2">
            <Upload size={16} strokeWidth={1.5} className="text-[var(--color-accent)]" />
            <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">Importera från Avanza</h2>
          </div>
          <button onClick={onClose} className="text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]">
            <X size={16} strokeWidth={1.5} />
          </button>
        </div>

        <div className="p-5 space-y-4 overflow-y-auto" style={{ maxHeight: "calc(80vh - 60px)" }}>
          {/* Step 1: Upload */}
          {!preview && (
            <div className="space-y-4">
              <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
                Exportera dina innehav från Avanza (Konto → Depå/ISK → Innehav → Exportera) och ladda upp CSV-filen här.
              </p>
              <div className="flex items-center gap-3">
                <input
                  type="file"
                  accept=".csv,.txt"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="flex-1 text-xs text-[var(--color-text-secondary)] file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-[var(--color-accent-soft)] file:text-[var(--color-accent)] hover:file:opacity-80"
                />
                <button
                  onClick={handleUpload}
                  disabled={!file || loading}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium text-white bg-[var(--color-accent)] disabled:opacity-40"
                >
                  {loading ? <Loader2 size={14} className="animate-spin" /> : <FileUp size={14} />}
                  {loading ? "Läser..." : "Förhandsgranska"}
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Preview */}
          {preview && (
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)]">
                <span>{preview.length} rader hittades</span>
                <span>
                  {totalWithTicker} mappade · {preview.length - totalWithTicker} omappade
                </span>
              </div>

              {/* Preview table */}
              <div className="space-y-1 max-h-64 overflow-y-auto">
                {preview.map((row, i) => {
                  const ticker = overrides[i]?.toUpperCase() || row.ticker;
                  const hasTicker = !!ticker;
                  return (
                    <div
                      key={i}
                      className={cn(
                        "flex items-center gap-2 px-3 py-2 rounded-lg text-xs border",
                        hasTicker
                          ? "bg-[var(--color-bg-elevated)] border-[var(--color-border)]"
                          : "bg-[var(--color-warn)]/5 border-[var(--color-warn)]/20",
                      )}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-[var(--color-text-primary)] truncate">{row.name}</div>
                        <div className="font-mono text-[var(--color-text-muted)] mt-0.5">
                          {row.shares != null ? `${row.shares} st` : ""}
                          {row.cost_basis != null ? ` @ ${row.cost_basis.toFixed(2)}` : ""}
                        </div>
                      </div>
                      {hasTicker ? (
                        <span className="font-mono font-medium text-[var(--color-accent)]">{ticker}</span>
                      ) : (
                        <input
                          value={overrides[i] || ""}
                          onChange={(e) => setOverrides((p) => ({ ...p, [i]: e.target.value }))}
                          placeholder="Ange ticker..."
                          className="w-28 px-2 py-1 rounded text-[11px] font-mono border bg-[var(--color-bg-surface)] border-[var(--color-warn)]/30 outline-none text-[var(--color-text-primary)]"
                        />
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Confirm buttons */}
              <div className="flex items-center gap-2 pt-2">
                <button
                  onClick={handleConfirm}
                  disabled={confirming || totalWithTicker === 0}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium text-white bg-[var(--color-accent)] disabled:opacity-40"
                >
                  {confirming ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                  {confirming ? "Importerar..." : `Importera ${totalWithTicker} innehav`}
                </button>
                <button
                  onClick={() => { setPreview(null); setFile(null); setOverrides({}); }}
                  className="px-4 py-2 rounded-lg text-xs border border-[var(--color-border)] text-[var(--color-text-muted)]"
                >
                  Börja om
                </button>
              </div>

              {preview.length - totalWithTicker > 0 && (
                <p className="text-[11px] text-[var(--color-warn)] flex items-center gap-1">
                  <AlertCircle size={12} strokeWidth={1.5} />
                  {preview.length - totalWithTicker} aktier kunde inte mappas automatiskt. Ange ticker manuellt ovan.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
