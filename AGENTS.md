# MarketScan — arbetsinstruktioner för AI

## Börja rätt, läs lite

Läs `SYSTEM_INDEX.md` först och därefter endast det kapitel under
`docs/codex/` som uppgiften kräver. Koden och live-verifiering vinner vid
konflikt. `STATUS.md` är nuläget; `HANDOFF.md`, `SYSTEM_AI.md`, planer och
arkiv är bakgrund eller historik, inte konkurrerande instruktioner.

## Samarbetsstil

Svara på svenska som en vanlig, insiktsfull AI-kollega. Börja med det användaren
frågar efter och förklara arbetet naturligt, utan automatiska statusrubriker,
checklistor eller verktygsnarration. Efter en ändring: säg vad som blev bättre
och nämn faktisk verifiering eller kvarvarande osäkerhet när det hjälper.
Föreslå nästa steg bara när användaren har ett meningsfullt val eller arbetet
inte är avslutat.

## Säkerhet och kvalitet

- Gissa inte om buggar, data eller drift: kontrollera kod, test eller live-data.
- `backend_worker/` får aldrig importeras av `apps/api/`.
- Skydda RLS, auth och service-role. Produktionsändringar, särskilt migrationer,
  kräver uttryckligt godkännande när de inte tydligt har begärts.
- Uppdatera relevant kapitel i `docs/codex/` när arkitektur eller aktivt
  beteende förändras; skriv inte om historik som om den vore nuläge.
