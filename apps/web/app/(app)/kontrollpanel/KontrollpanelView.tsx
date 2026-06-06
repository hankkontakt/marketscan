"use client";

import * as Tabs from "@radix-ui/react-tabs";
import { Activity, RefreshCw, Globe, BarChart2, Settings } from "lucide-react";
import { StatusSection, PipelineSection, UniversumSection, MattSection, SettingsSection } from "@/components/admin/AdminSections";
import { KpiCard, StatusPill, RunsTable, DistTable } from "@/components/admin/StatusHelpers";
import { useQuery } from "@tanstack/react-query";

export function KontrollpanelView() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Kontrollpanel</h1>

      <Tabs.Root defaultValue="Status">
        {/* Section tabs */}
        <Tabs.List className="flex gap-1 flex-wrap">
          <Tabs.Trigger
            value="Status"
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs transition-colors
                       data-[state=active]:bg-[var(--color-accent)] data-[state=active]:text-white
                       data-[state=inactive]:bg-[var(--color-bg-surface)] data-[state=inactive]:text-[var(--color-text-secondary)]
                       data-[state=inactive]:border data-[state=inactive]:border-[var(--color-border)]
                       data-[state=inactive]:hover:border-[var(--color-border-strong)]"
          >
            <Activity size={13} strokeWidth={1.5} />
            Status
          </Tabs.Trigger>
          <Tabs.Trigger
            value="Pipeline"
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs transition-colors
                       data-[state=active]:bg-[var(--color-accent)] data-[state=active]:text-white
                       data-[state=inactive]:bg-[var(--color-bg-surface)] data-[state=inactive]:text-[var(--color-text-secondary)]
                       data-[state=inactive]:border data-[state=inactive]:border-[var(--color-border)]
                       data-[state=inactive]:hover:border-[var(--color-border-strong)]"
          >
            <RefreshCw size={13} strokeWidth={1.5} />
            Pipeline
          </Tabs.Trigger>
          <Tabs.Trigger
            value="Universum"
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs transition-colors
                       data-[state=active]:bg-[var(--color-accent)] data-[state=active]:text-white
                       data-[state=inactive]:bg-[var(--color-bg-surface)] data-[state=inactive]:text-[var(--color-text-secondary)]
                       data-[state=inactive]:border data-[state=inactive]:border-[var(--color-border)]
                       data-[state=inactive]:hover:border-[var(--color-border-strong)]"
          >
            <Globe size={13} strokeWidth={1.5} />
            Universum
          </Tabs.Trigger>
          <Tabs.Trigger
            value="Mått"
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs transition-colors
                       data-[state=active]:bg-[var(--color-accent)] data-[state=active]:text-white
                       data-[state=inactive]:bg-[var(--color-bg-surface)] data-[state=inactive]:text-[var(--color-text-secondary)]
                       data-[state=inactive]:border data-[state=inactive]:border-[var(--color-border)]
                       data-[state=inactive]:hover:border-[var(--color-border-strong)]"
          >
            <BarChart2 size={13} strokeWidth={1.5} />
            Mått
          </Tabs.Trigger>
          <Tabs.Trigger
            value="Inställningar"
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs transition-colors
                       data-[state=active]:bg-[var(--color-accent)] data-[state=active]:text-white
                       data-[state=inactive]:bg-[var(--color-bg-surface)] data-[state=inactive]:text-[var(--color-text-secondary)]
                       data-[state=inactive]:border data-[state=inactive]:border-[var(--color-border)]
                       data-[state=inactive]:hover:border-[var(--color-border-strong)]"
          >
            <Settings size={13} strokeWidth={1.5} />
            Inställningar
          </Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content value="Status"><StatusSection /></Tabs.Content>
        <Tabs.Content value="Pipeline"><PipelineSection /></Tabs.Content>
        <Tabs.Content value="Universum"><UniversumSection /></Tabs.Content>
        <Tabs.Content value="Mått"><MattSection /></Tabs.Content>
        <Tabs.Content value="Inställningar"><SettingsSection /></Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
