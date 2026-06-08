"use client";

import { useState, useRef } from "react";
import {
  Upload, X, Check, Loader2, AlertCircle, FileUp,
  ChevronRight, Info, AlertTriangle, FileText,
} from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface ImportPreviewItem {
  name: string;
  ticker: string | null;
  shares: number | null;
  cost_basis: number | null;
  current_price: number | null;   // derived from marknadsvarde / shares
  marknadsvarde: number | null;   // total market value at export time
  mapped: boolean;
  purchase_date: string | null;
  isin: string | null;
  av_typ: string | null; // "STOCK" | "FUND" | ""
}

interface Props {
  onClose: () => void;
}

// ──── Step 0: file upload + instructions ────────────────────────────────────

function Step0({
  positionerFile,
  inkopskurserFile,
  onPositioner,
  onInkopskurser,
  onNext,
  loading,
}: {
  positionerFile: File | null;
  inkopskurserFile: File | null;
  onPositioner: (f: File | null) => void;
  onInkopskurser: (f: File | null) => void;
  onNext: () => void;
  loading: boolean;
}) {
  return (
    <div className="space-y-5">
      {/* How-to instructions */}
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-4 space-y-3">
        <p className="text-xs font-semibold text-[var(--color-text-primary)]">
          Hur du exporterar från Avanza
        </p>
        <ol className="space-y-2">
          {[
            "Logga in på Avanza.se",
            "Klicka på \"Min ekonomi\" i toppmenyn",
            "Välj \"Analys\" i undermenyn",
            "Scrolla ner till avsnittet \"Exportera data\"",
          ].map((step, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-[var(--color-text-secondary)]">
              <span className="flex-none w-5 h-5 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)] text-[10px] font-bold flex items-center justify-center mt-0.5">
                {i + 1}
              </span>
              {step}
            </li>
          ))}
        </ol>

        {/* File list */}
        <div className="pt-1 space-y-2">
          <p className="text-[11px] font-medium text-[var(--color-text-muted)]">
            Ladda ner dessa två filer:
          </p>
          <div className="space-y-1.5">
            <FileRow
              label="Positioner (krävs)"
              desc={'"Mitt innehav fördelat per konto" → Ladda ner som .csv'}
              required
            />
            <FileRow
              label="Inköpskurs (valfri)"
              desc={'"Inköpskurs" → Ladda ner historisk inköpskurs som .csv'}
              required={false}
            />
          </div>
        </div>
      </div>

      {/* File inputs */}
      <div className="space-y-3">
        <FileInput
          label="Positioner-fil"
          hint="positioner_per_konto.csv eller positioner_sammanstallda.csv"
          required
          file={positionerFile}
          onChange={onPositioner}
        />
        <FileInput
          label="Inköpskurs-fil (valfri)"
          hint="inkopskurs_XXXXXX_ÅÅÅÅ-MM-DD.csv — ger automatiskt köpdatum"
          required={false}
          file={inkopskurserFile}
          onChange={onInkopskurser}
        />
      </div>

      <button
        onClick={onNext}
        disabled={!positionerFile || loading}
        className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium text-white disabled:opacity-40 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] transition-colors"
      >
        {loading ? (
          <><Loader2 size={14} className="animate-spin" />Analyserar...</>
        ) : (
          <><FileUp size={14} />Förhandsgranska</>
        )}
      </button>
    </div>
  );
}

function FileRow({ label, desc, required }: { label: string; desc: string; required: boolean }) {
  return (
    <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-[var(--color-bg-surface)] border border-[var(--color-border)]">
      <FileText size={13} className="text-[var(--color-accent)] mt-0.5 shrink-0" />
      <div className="min-w-0">
        <div className="text-xs font-medium text-[var(--color-text-primary)]">
          {label}
          {required && <span className="ml-1 text-[var(--color-down)] text-[10px]">*</span>}
        </div>
        <div className="text-[11px] text-[var(--color-text-muted)] mt-0.5">{desc}</div>
      </div>
    </div>
  );
}

function FileInput({
  label,
  hint,
  required,
  file,
  onChange,
}: {
  label: string;
  hint: string;
  required: boolean;
  file: File | null;
  onChange: (f: File | null) => void;
}) {
  const ref = useRef<HTMLInputElement>(null);
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-[var(--color-text-secondary)]">
        {label}
        {required && <span className="text-[var(--color-down)] ml-0.5">*</span>}
      </label>
      <div
        className={cn(
          "flex items-center gap-2 px-3 py-2.5 rounded-lg border text-xs cursor-pointer transition-colors",
          file
            ? "border-[var(--color-accent)]/40 bg-[var(--color-accent-soft)]"
            : "border-[var(--color-border)] bg-[var(--color-bg-elevated)] hover:border-[var(--color-border-strong)]",
        )}
        onClick={() => ref.current?.click()}
      >
        <Upload size={13} className={file ? "text-[var(--color-accent)]" : "text-[var(--color-text-muted)]"} />
        <span className={file ? "text-[var(--color-accent)] font-medium truncate" : "text-[var(--color-text-muted)] truncate"}>
          {file ? file.name : hint}
        </span>
        {file && (
          <button
            className="ml-auto text-[var(--color-text-muted)] hover:text-[var(--color-down)] shrink-0"
            onClick={(e) => { e.stopPropagation(); onChange(null); }}
            aria-label="Ta bort fil"
          >
            <X size={12} />
          </button>
        )}
      </div>
      <input ref={ref} type="file" accept=".csv,.txt" className="hidden"
             onChange={(e) => onChange(e.target.files?.[0] ?? null)} />
    </div>
  );
}

// ──── Step 1: preview ────────────────────────────────────────────────────────

function ReturnBadge({ cost, current }: { cost: number | null; current: number | null }) {
  if (!cost || !current || cost <= 0) return null;
  const pct = ((current - cost) / cost) * 100;
  const pos = pct >= 0;
  return (
    <span className={cn("text-[11px] font-mono", pos ? "text-emerald-400" : "text-red-400")}>
      {pos ? "+" : ""}{pct.toFixed(1)}%
    </span>
  );
}

function Step1({
  preview,
  overrides,
  onOverride,
  onConfirm,
  onBack,
  confirming,
}: {
  preview: ImportPreviewItem[];
  overrides: Record<number, string>;
  onOverride: (i: number, v: string) => void;
  onConfirm: () => void;
  onBack: () => void;
  confirming: boolean;
}) {
  const [tab, setTab] = useState<"aktier" | "fonder">("aktier");

  const stocks = preview.filter((r) => r.av_typ !== "FUND");
  const funds  = preview.filter((r) => r.av_typ === "FUND");

  const totalWithTicker = stocks.filter((r) => {
    const idx = preview.indexOf(r);
    return !!(overrides[idx]?.toUpperCase() || r.ticker);
  }).length;

  const unmappedCount = stocks.filter((r) => {
    const idx = preview.indexOf(r);
    return !(overrides[idx]?.toUpperCase() || r.ticker);
  }).length;

  const hasPurchaseDates = preview.some((r) => r.purchase_date);
  const totalImport = totalWithTicker + funds.length;

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)]">
        <span>
          {stocks.length} aktier · {funds.length} fonder
        </span>
        <span className={unmappedCount > 0 ? "text-[var(--color-warn)]" : "text-[var(--color-up)]"}>
          {totalWithTicker} aktier mappade{unmappedCount > 0 ? ` · ${unmappedCount} omappade` : ""}
        </span>
      </div>

      {/* Info: purchase dates auto-filled */}
      {hasPurchaseDates && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--color-accent-soft)] border border-[var(--color-accent)]/20 text-[11px] text-[var(--color-accent)]">
          <Info size={12} className="shrink-0" />
          Köpdatum hämtades automatiskt från inköpskurs-filen och sparas som transaktioner.
        </div>
      )}

      {/* Tab switcher (only show if there are both stocks and funds) */}
      {stocks.length > 0 && funds.length > 0 && (
        <div className="flex gap-1">
          {(["aktier", "fonder"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                "px-3 py-1 rounded-lg text-xs font-medium transition-colors",
                tab === t
                  ? "bg-[var(--color-accent)] text-white"
                  : "bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]",
              )}
            >
              {t === "aktier" ? `Aktier (${stocks.length})` : `Fonder (${funds.length})`}
            </button>
          ))}
        </div>
      )}

      {/* Preview list */}
      <div className="space-y-1 max-h-64 overflow-y-auto">
        {/* Stock rows */}
        {tab === "aktier" && stocks.map((row) => {
          const i = preview.indexOf(row);
          const ticker = overrides[i]?.toUpperCase() || row.ticker;
          const hasTicker = !!ticker;
          return (
            <div
              key={i}
              className={cn(
                "grid grid-cols-[1fr_auto] gap-2 px-3 py-2 rounded-lg border text-xs",
                hasTicker
                  ? "bg-[var(--color-bg-elevated)] border-[var(--color-border)]"
                  : "bg-[var(--color-warn)]/5 border-[var(--color-warn)]/25",
              )}
            >
              <div className="min-w-0 space-y-0.5">
                <div className="font-medium text-[var(--color-text-primary)] truncate">{row.name}</div>
                <div className="font-mono text-[var(--color-text-muted)] flex flex-wrap gap-x-3">
                  {row.shares != null && <span>{row.shares} st</span>}
                  {row.cost_basis != null && <span>GAV {row.cost_basis.toFixed(2)} kr</span>}
                  {row.purchase_date && (
                    <span className="text-[var(--color-accent)]">köpt {row.purchase_date}</span>
                  )}
                </div>
              </div>
              <div className="flex items-center">
                {hasTicker ? (
                  <span className="font-mono font-semibold text-[var(--color-accent)]">{ticker}</span>
                ) : (
                  <input
                    value={overrides[i] || ""}
                    onChange={(e) => onOverride(i, e.target.value)}
                    placeholder="Ange ticker..."
                    className="w-28 px-2 py-1 rounded text-[11px] font-mono border bg-[var(--color-bg-surface)] border-[var(--color-warn)]/40 outline-none text-[var(--color-text-primary)] focus:border-[var(--color-warn)]"
                  />
                )}
              </div>
            </div>
          );
        })}

        {/* Fund rows */}
        {(tab === "fonder" || stocks.length === 0) && funds.map((row) => {
          const i = preview.indexOf(row);
          const returnPct = row.cost_basis && row.current_price && row.cost_basis > 0
            ? ((row.current_price - row.cost_basis) / row.cost_basis) * 100
            : null;
          return (
            <div
              key={i}
              className="px-3 py-2.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-elevated)] text-xs space-y-1"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="font-medium text-[var(--color-text-primary)] truncate">{row.name}</div>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--color-bg-surface)] text-[var(--color-text-muted)] shrink-0">FOND</span>
              </div>
              <div className="font-mono text-[var(--color-text-muted)] flex flex-wrap gap-x-3">
                {row.shares != null && <span>{row.shares} andelar</span>}
                {row.cost_basis != null && <span>GAV {row.cost_basis.toFixed(2)} kr</span>}
                {row.current_price != null && (
                  <span className="text-[var(--color-text-secondary)]">
                    kurs {row.current_price.toFixed(2)} kr
                  </span>
                )}
                {returnPct != null && (
                  <ReturnBadge cost={row.cost_basis} current={row.current_price} />
                )}
                {row.marknadsvarde != null && (
                  <span className="text-[var(--color-text-secondary)]">
                    värde {row.marknadsvarde.toLocaleString("sv-SE", { maximumFractionDigits: 0 })} kr
                  </span>
                )}
                {row.purchase_date && (
                  <span className="text-[var(--color-accent)]">köpt {row.purchase_date}</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Unmapped warning */}
      {unmappedCount > 0 && tab === "aktier" && (
        <p className="flex items-center gap-1.5 text-[11px] text-[var(--color-warn)]">
          <AlertTriangle size={12} strokeWidth={1.5} />
          {unmappedCount} aktier saknar ticker — ange dem manuellt ovan för att inkludera dem.
        </p>
      )}

      {/* Fund info */}
      {tab === "fonder" && funds.length > 0 && (
        <p className="text-[11px] text-[var(--color-text-muted)]">
          Kurs och värde baseras på exporten från Avanza. Fondpriser uppdateras när du importerar på nytt.
        </p>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 pt-1">
        <button
          onClick={onConfirm}
          disabled={confirming || totalImport === 0}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium text-white disabled:opacity-40 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] transition-colors"
        >
          {confirming ? (
            <><Loader2 size={14} className="animate-spin" />Importerar...</>
          ) : (
            <><Check size={14} />Importera {totalWithTicker} aktier{funds.length > 0 ? ` + ${funds.length} fonder` : ""}</>
          )}
        </button>
        <button
          onClick={onBack}
          className="px-4 py-2 rounded-lg text-xs border border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors"
        >
          Tillbaka
        </button>
      </div>
    </div>
  );
}

// ──── Root modal ─────────────────────────────────────────────────────────────

export function ImportModal({ onClose }: Props) {
  const [step, setStep]               = useState<0 | 1>(0);
  const [positionerFile, setPositionerFile]     = useState<File | null>(null);
  const [inkopskurserFile, setInkopskurserFile] = useState<File | null>(null);
  const [preview, setPreview]         = useState<ImportPreviewItem[] | null>(null);
  const [overrides, setOverrides]     = useState<Record<number, string>>({});
  const [loading, setLoading]         = useState(false);
  const [confirming, setConfirming]   = useState(false);

  async function handlePreview() {
    if (!positionerFile) return;
    setLoading(true);
    try {
      const positionerText  = await positionerFile.text();
      const inkopskurserText = inkopskurserFile ? await inkopskurserFile.text() : null;

      const data = await api<{
        rows: ImportPreviewItem[];
        mapped_count: number;
        unmapped_count: number;
        total: number;
      }>("/api/portfolio/import/avanza/preview", {
        method: "POST",
        body: JSON.stringify({
          positioner_csv: positionerText,
          inkopskurser_csv: inkopskurserText ?? null,
        }),
      });

      setPreview(data.rows);
      setOverrides({});
      setStep(1);
    } catch (err: any) {
      toast.error(err.message || "Kunde inte läsa CSV-filerna");
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
      const res = await api<{ created: number }>("/api/portfolio/import/confirm", {
        method: "POST",
        body: JSON.stringify({ rows: resolved }),
      });
      toast.success(`${res.created} innehav importerade`);
      onClose();
      window.location.reload();
    } catch (err: any) {
      toast.error(err.message || "Kunde inte bekräfta import");
    } finally {
      setConfirming(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div
        className="w-full max-w-lg rounded-2xl shadow-2xl bg-[var(--color-bg-surface)] border border-[var(--color-border-strong)]"
        style={{ maxHeight: "88vh" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--color-border)]">
          <div className="flex items-center gap-2">
            <Upload size={16} strokeWidth={1.5} className="text-[var(--color-accent)]" />
            <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
              Importera från Avanza
            </h2>
            {/* Step breadcrumb */}
            <div className="flex items-center gap-1 ml-2">
              {(["Ladda upp", "Granska"] as const).map((s, i) => (
                <span key={s} className="flex items-center gap-1">
                  {i > 0 && <ChevronRight size={11} className="text-[var(--color-text-muted)]" />}
                  <span
                    className={cn(
                      "text-[11px]",
                      i === step
                        ? "text-[var(--color-accent)] font-medium"
                        : "text-[var(--color-text-muted)]",
                    )}
                  >
                    {s}
                  </span>
                </span>
              ))}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors"
          >
            <X size={16} strokeWidth={1.5} />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 overflow-y-auto" style={{ maxHeight: "calc(88vh - 64px)" }}>
          {step === 0 && (
            <Step0
              positionerFile={positionerFile}
              inkopskurserFile={inkopskurserFile}
              onPositioner={setPositionerFile}
              onInkopskurser={setInkopskurserFile}
              onNext={handlePreview}
              loading={loading}
            />
          )}
          {step === 1 && preview && (
            <Step1
              preview={preview}
              overrides={overrides}
              onOverride={(i, v) => setOverrides((p) => ({ ...p, [i]: v }))}
              onConfirm={handleConfirm}
              onBack={() => setStep(0)}
              confirming={confirming}
            />
          )}
        </div>
      </div>
    </div>
  );
}
