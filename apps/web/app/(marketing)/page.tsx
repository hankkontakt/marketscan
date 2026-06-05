import Link from "next/link";
import { TrendingUp, BarChart2, Shield, Star, ArrowRight, CheckCircle } from "lucide-react";

export default function LandingPage() {
  return (
    <main className="min-h-dvh flex flex-col bg-[var(--color-bg-base)]">

      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-5 max-w-6xl mx-auto w-full">
        <div className="flex items-center gap-2">
          <TrendingUp size={20} strokeWidth={1.5} className="text-[var(--color-accent)]" />
          <span className="font-bold text-lg text-[var(--color-text-primary)]">MarketScan</span>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/login"
                className="text-sm font-medium px-4 py-2 rounded-xl transition-colors text-[var(--color-text-secondary)]">
            Logga in
          </Link>
          <Link href="/register"
                className="text-sm font-semibold px-4 py-2 rounded-xl text-white transition-colors bg-[var(--color-accent)]">
            Kom igång gratis
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center text-center px-6 py-20">
        <div className="max-w-2xl mx-auto space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border text-[var(--color-accent)]"
               style={{ background: "var(--color-bg-elevated)", borderColor: "var(--color-border)" }}>
            <span className="w-1.5 h-1.5 rounded-full bg-current" />
            Uppdateras automatiskt varje dag
          </div>

          <h1 className="text-4xl md:text-5xl font-bold leading-tight text-[var(--color-text-primary)]">
            Aktieanalys du faktiskt
            <br />
            <span className="text-[var(--color-accent)]">förstår och litar på</span>
          </h1>

          <p className="text-lg leading-relaxed max-w-xl mx-auto text-[var(--color-text-secondary)]">
            Systemet betygsätter 800+ aktier varje dag baserat på värde, kvalitet och momentum.
            Du ser direkt vilka som är köpvärda — utan att behöva vara finansexpert.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link href="/register"
                  className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3 rounded-xl
                             text-sm font-semibold text-white transition-colors bg-[var(--color-accent)]">
              Skapa gratis konto
              <ArrowRight size={16} strokeWidth={2} />
            </Link>
            <Link href="/screener"
                  className="w-full sm:w-auto text-sm font-medium px-6 py-3 rounded-xl border transition-colors
                             text-[var(--color-text-secondary)]"
                  style={{ borderColor: "var(--color-border)", background: "var(--color-bg-surface)" }}>
              Utforska aktier utan konto
            </Link>
          </div>

          {/* Trust markers */}
          <div className="flex items-center justify-center gap-6 pt-2 flex-wrap">
            {["800+ aktier analyserade", "Uppdateras dagligen", "Gratis att använda"].map((t) => (
              <div key={t} className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)]">
                <CheckCircle size={13} strokeWidth={1.5} className="text-[var(--color-up)]" />
                {t}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="px-6 pb-20 max-w-5xl mx-auto w-full">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {[
            {
              icon: BarChart2,
              title: "Betyg du förstår",
              desc: "Varje aktie får ett betyg 0–100 baserat på 8 faktorer. Klicka på valfritt värde för en tydlig förklaring.",
              color: "var(--color-accent)",
            },
            {
              icon: Star,
              title: "Bevaka & få larm",
              desc: "Bevaka aktier du är intresserad av. Sätt prisriktkurslarm — systemet meddelar dig när kursen når dit.",
              color: "var(--color-up)",
            },
            {
              icon: Shield,
              title: "Transparent — inga svarta lådor",
              desc: "Alla poäng är spårbara. Se exakt vilka faktorer som driver varje betyg och vad de betyder.",
              color: "var(--color-warn)",
            },
          ].map(({ icon: Icon, title, desc, color }) => (
            <div key={title}
                 className="rounded-2xl p-6 border"
                 style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
              <div className="w-9 h-9 rounded-xl flex items-center justify-center mb-4"
                   style={{ background: color + "14" }}>
                <Icon size={18} strokeWidth={1.5} style={{ color }} />
              </div>
              <h3 className="text-sm font-semibold mb-2 text-[var(--color-text-primary)]">{title}</h3>
              <p className="text-xs leading-relaxed text-[var(--color-text-secondary)]">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t px-8 py-5 flex items-center justify-between max-w-6xl mx-auto w-full"
              style={{ borderColor: "var(--color-border)" }}>
        <span className="text-xs text-[var(--color-text-muted)]">MarketScan — personlig aktieanalys</span>
        <span className="text-xs text-[var(--color-text-muted)]">Investering innebär alltid risk</span>
      </footer>
    </main>
  );
}
