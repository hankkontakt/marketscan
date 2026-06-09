import { TopBar } from "@/components/layout/TopBar";
import { CommandPalette } from "@/components/command/CommandPalette";
import { ExperienceProvider } from "@/components/providers/ExperienceProvider";
import { OnboardingModal } from "@/components/onboarding/OnboardingModal";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <ExperienceProvider>
      <div className="app-layout">
        <TopBar />
        <main className="app-main">
          {children}
        </main>
        <CommandPalette />
        <OnboardingModal />
      </div>
    </ExperienceProvider>
  );
}
