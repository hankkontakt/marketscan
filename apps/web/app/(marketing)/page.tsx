import Link from "next/link";
import { TrendingUp, BarChart2, Shield, Zap } from "lucide-react";

export default function LandingPage() {
  return (
    <main className="min-h-dvh flex flex-col items-center px-4"
          style={{ background: "var(--color-bg-base)" }}>
      {/* Nav */}
      <nav className="w-full max-w-5xl flex items-center justify-between py-5">
        <div className="flex items-center gap-2">
          <TrendingUp size={20} strokeWidth={1.5} style={{ color: "var(--color-accent)" }} />
          <span className="font-bold text-[var(--color-text-primary)]">MarketScan</span>
        </div>
        <Link href="/login"
              className="px-4 py-1.5 rounded-lg text-sm font-medium border transition-colors
                         border-[var(--color-border)] text-[var(--color-text-secondary)]
                         hover:border-[var(--color-border-strong)] hover:text-[var(--color-text-primary)]">
          Logga in
        </Link>
      </nav>

      {/* Hero */}
      <div className="max-w-3xl text-center py-24 space-y-6">
        <h1 className="text-4xl md:text-5xl font-bold text-[var(--color-text-primary)] leading-tight">
          Professionell aktieanalys<br />
          <span style={{ color: "var(--color-accent)" }}>för svenska marknader</span>
        </h1>
        <p className="text-base text-[var(--color-text-secondary)] max-w-lg mx-auto leading-relaxed">
          Kvantitativ screening, AI-analys och portföljöversikt — allt i ett gränssnitt
          inspirerat av Bloomberg, Avanza och Lysa.
        </p>
        <div className="flex items-center justify-center gap-3 flex-wrap">
          <Link href="/login"
                className="px-6 py-2.5 rounded-xl text-sm font-semibold transition-colors
                           bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)]">
            Kom igång
          </Link>
          <Link href="/screener"
                className="px-6 py-2.5 rounded-xl text-sm font-medium border transition-colors
                           border-[var(--color-border)] text-[var(--color-text-secondary)]
                           hover:border-[var(--color-border-strong)]">
            Utforska screener
          </Link>
        </div>
      </div>

      {/* Feature cards */}
      <div className="w-full max-w-5xl grid grid-cols-1 md:grid-cols-3 gap-4 pb-16">
        {[
          {
            icon: BarChart2,
            title: "Sammanslagen screener",
            desc: "En motor för alla segment — stora, medelstora, småbolag och mikrobolag i samma vy.",
          },
          {
            icon: Zap,
            title: "Analyskommittén",
            desc: "Tre AI-analytiker (teknisk, fundamental, sentiment) + ordförande med konfidensmätare.",
          },
          {
            icon: Shield,
            title: "Transparent scoring",
            desc: "8 faktorbetyg med förklaringar. Inga svarta lådor — alla poäng är spårbara.",
          },
        ].map(({ icon: Icon, title, desc }) => (
          <div key={title}
               className="rounded-xl p-5 border"
               style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
            <Icon size={20} strokeWidth={1.5} style={{ color: "var(--color-accent)", marginBottom: 12 }} />
            <h3 className="text-sm font-semibold mb-2 text-[var(--color-text-primary)]">{title}</h3>
            <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">{desc}</p>
          </div>
        ))}
      </div>
    </main>
  );
}
