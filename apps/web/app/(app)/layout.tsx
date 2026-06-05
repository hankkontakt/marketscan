import { NavRail } from "@/components/layout/NavRail";
import { TopBar } from "@/components/layout/TopBar";
import { CommandPalette } from "@/components/command/CommandPalette";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-layout">
      <NavRail />
      <TopBar />
      <main className="app-main">
        {children}
      </main>
      <CommandPalette />
    </div>
  );
}
