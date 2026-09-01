# Ultimate Rebuild v3 — Baseline (2026-09-01)

## Scope of this implementation slice

This branch establishes the first safe V3 boundary. It does not declare a V3
cutover: `scan_results` and V1/V2 surfaces remain live until staging evidence
proves the complete pipeline, identity backfill and product migration.

## Verified repository facts

- The repository head is `e5052dd`, the commit reviewed by the supplied V3
  specification.
- The existing V2 decision router recomputes MasterRank, setup and risk during
  HTTP requests, uses a benchmark-only in-memory Security Master and supplies
  synthetic fallback rows/UUIDs. It is therefore not a canonical production
  decision path.
- The V3 API is disabled by default and has no fixture fallback. A disabled
  route returns `404`; an enabled route with no published snapshot returns an
  explicit `404`/`503`, never a fabricated decision.
- The connected production migration ledger ends at `082`. Local `083` is the
  next migration and has passed a clean local reset. Its number must still be
  revalidated against a staging ledger before any remote application.
- Six duplicate-numbered, incomplete V2 migration drafts were removed from the
  active migration chain and retained under `supabase/migrations_archive/`.
  This makes the migration ledger fail closed instead of silently selecting an
  arbitrary file for versions `012` through `017`.

## Implemented contract

1. Security identity is database-backed (`issuers`, `securities`, `listings`,
   ticker aliases) and separates a ticker alias from `listing_id`.
2. Observations carry a metric catalog, canonical unit, source payload hash,
   availability time and a point-in-time check.
3. Workers stage immutable manifests and call one database function to publish
   a non-empty snapshot atomically. That function rejects actionable decisions
   for inactive listings.
4. API V3 reads only the currently published projection. It performs no quant
   calculation and does not import worker code.
5. Public roles can read published projections only; raw payloads, quarantine
   records and writes remain service-only.

## Local proof (2026-09-01)

- `supabase db reset --local` completed through migration `083` and seed data.
- `supabase migration list --local` reports matching local/remote entries
  `001` through `083` in the local database.
- `supabase db lint --local` and both security/performance advisors report no
  ERROR-level issues.
- As `anon`, REST can read `scan_results` but receives an empty result from
  `pipeline_runs`; V3's published projection is empty until a worker publishes
  a snapshot.
- A staged valid manifest atomically publishes and updates the pointer. An
  actionable manifest for a `MERGED` listing raises an error and is not
  published.

## Required next gates

1. Create a staging database branch and verify the real migration head before
   applying the migration. Do not apply it to production from this workspace.
2. Add full-universe Security Master backfill and corporate-action ingestion;
   prove inactive listings (including CPRX) cannot become actionable.
3. Make the worker build V3 manifests from normalized observations and invoke
   `DecisionManifestPublisher` only after unit, PIT, coverage and run gates
   pass.
4. Remove `backend_worker` imports from V2 API code, migrate product surfaces
   to V3 behind real runtime flags, and add database RLS/integration tests.
