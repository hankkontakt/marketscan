import React from "react";

export function SectionCard({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="rounded-xl p-5 border space-y-5 bg-[var(--color-bg-surface)] border-[var(--color-border)]"
    >
      {children}
    </div>
  );
}

export function SectionTitle({ icon: Icon, title }: { icon: React.ElementType; title: string }) {
  return (
    <div className="flex items-center gap-2">
      <Icon size={16} strokeWidth={1.5} className="text-[var(--color-accent)]" />
      <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
        {title}
      </h2>
    </div>
  );
}
