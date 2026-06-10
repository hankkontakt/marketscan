"use client";

import { Star } from "lucide-react";

export function BeginnerCTA() {
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
        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium
                   bg-green-600 text-white hover:bg-green-700 transition-colors"
      >
        <Star size={14} strokeWidth={1.5} />
        Lägg i bevakning
      </button>
    </div>
  );
}
