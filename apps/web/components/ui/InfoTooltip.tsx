"use client";

import React from "react";
import * as RadixTooltip from "@radix-ui/react-tooltip";

interface Props {
  text: string;
  side?: "top" | "bottom" | "left" | "right";
}

/**
 * InfoTooltip — small ⓘ icon that shows a description on hover.
 * Place next to any label to explain what the value means.
 *
 * Usage:
 *   <span>P/E <InfoTooltip text="Pris/vinst-kvot. Visar hur dyrt aktien är relativt sin vinst." /></span>
 */
export const InfoTooltip = React.memo(function InfoTooltip({ text, side = "top" }: Props) {
  return (
    <RadixTooltip.Provider delayDuration={150}>
      <RadixTooltip.Root>
        <RadixTooltip.Trigger asChild>
          <button
            tabIndex={-1}
            aria-label="Mer information"
            className="inline-flex items-center justify-center align-middle ml-1 shrink-0
                       w-3.5 h-3.5 rounded-full text-[9px] font-bold leading-none
                       border cursor-help select-none
                       text-[var(--color-text-muted)] border-[var(--color-border-strong)]
                       hover:text-[var(--color-accent)] hover:border-[var(--color-accent)]
                       transition-colors"
          >
            i
          </button>
        </RadixTooltip.Trigger>

        <RadixTooltip.Portal>
          <RadixTooltip.Content
            side={side}
            sideOffset={5}
            className="max-w-56 px-3 py-2 text-xs rounded-xl shadow-lg z-[100]
                       leading-relaxed"
            style={{
              background: "var(--color-bg-surface)",
              border: "1px solid var(--color-border-strong)",
              color: "var(--color-text-secondary)",
              boxShadow: "0 4px 20px rgba(0,0,0,0.12)",
            }}
          >
            {text}
            <RadixTooltip.Arrow
              style={{ fill: "var(--color-border-strong)" }}
            />
          </RadixTooltip.Content>
        </RadixTooltip.Portal>
      </RadixTooltip.Root>
    </RadixTooltip.Provider>
  );
});
