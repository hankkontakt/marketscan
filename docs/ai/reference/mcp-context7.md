# Context7 MCP Reference

Denna referens läses **endast vid behov** när Context7-verktyg anropas för dokumentations- eller bibliotekssökning.

## Användningsmönster
- Använd context7_resolve_library_id för att slå upp officiella biblioteks-ID:n.
- Använd context7_query_docs för att hämta API-dokumentation för externa ramverk (FastAPI, Next.js, Drizzle, etc.).
- Undvik breda/upprepade anrop i samma session för att spara token-cache.
