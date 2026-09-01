"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { toast } from "sonner";

export function useWatchlistToggle() {
  const qc = useQueryClient();

  const add = useMutation({
    mutationFn: (ticker: string) =>
      api(`/api/watchlist/${ticker}`, { method: "POST" }),
    onSuccess: (_, ticker) => {
      qc.invalidateQueries({ queryKey: ["watchlist"] });
      toast.success(`${ticker} har lagts till i bevakningslistan.`);
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Kunde inte lägga till i bevakningslistan.";
      toast.error(msg);
    },
  });

  const remove = useMutation({
    mutationFn: (ticker: string) =>
      api(`/api/watchlist/${ticker}`, { method: "DELETE" }),
    onSuccess: (_, ticker) => {
      qc.invalidateQueries({ queryKey: ["watchlist"] });
      toast.success(`${ticker} togs bort från bevakningslistan.`);
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Kunde inte ta bort från bevakningslistan.";
      toast.error(msg);
    },
  });

  return { add, remove };
}
