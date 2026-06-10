"use client";

import { Star, Loader2 } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { toast } from "sonner";

export function BeginnerCTA({ ticker }: { ticker: string }) {
  const qc = useQueryClient();

  const addWatch = useMutation({
    mutationFn: () => api(`/api/watchlist/${ticker}`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["watchlist"] });
      toast.success("Bevakning tillagd");
    },
    onError: () => toast.error("Logga in för att bevaka aktier"),
  });
  return (
    <div
      className="rounded-xl border p-6 text-center space-y-4"
      style={{
        backgroundColor: "#f0fdf4",
        borderColor: "#bbf7d0",
      }}
    >
      <div className="flex items-center justify-center gap-2">
        <span className="text-xl">🎯</span>
        <h3 className="text-sm font-bold text-green-800">
          Vill du följa den här aktien?
        </h3>
      </div>

      <p className="text-xs text-green-700 leading-relaxed max-w-sm mx-auto">
        Lägg den i din bevakningslista och följ hur omdömet utvecklas under
        de kommande 30 dagarna.
      </p>

      <p className="text-xs text-green-600 leading-relaxed">
        Inga köp, ingen risk — bara lärande.
      </p>

      <button
        onClick={() => addWatch.mutate()}
        disabled={addWatch.isPending}
        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium
                   bg-green-600 text-white hover:bg-green-700 transition-colors disabled:opacity-50"
      >
        {addWatch.isPending ? (
          <Loader2 size={14} className="animate-spin" />
        ) : (
          <Star size={14} strokeWidth={1.5} />
        )}
        Lägg i bevakning
      </button>
    </div>
  );
}
