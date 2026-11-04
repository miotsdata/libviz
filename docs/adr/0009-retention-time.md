# 9 — Retention time as a spectrum column; migrate on open

**Status:** Accepted (2026-11-04)

## Context

Spectral-search users need the library spectrum's RT next to each hit.
Until now RT only existed as free metadata, under whatever key the source
used: `rt_min` from the builder, `RETENTIONTIME`/`RT`/`RTINSECONDS` from
MSP. The values were text, the units varied, and the field couldn't be
queried.

## Decision

- **`spectrum.rt`**: a nullable `Float` in **minutes**, indexed (migration
  `b5d1e2f3a4c7`). NULL means unknown. RT is not part of the spectrum's
  identity, so the unique constraint is unchanged.
- **The migration copies** the first parsable RT metadata key into `rt`
  (`rt_min`, `RETENTIONTIME`, `RETENTION_TIME`, `RT`, `RTINMINUTES`;
  `RTINSECONDS` ÷ 60). It keeps the metadata as provenance. Free text such
  as "n/a" stays metadata only.
- **MSP:**
  - Import puts numeric RT keys into `rt` and doesn't store them as
    metadata. A bare `RETENTIONTIME`/`RT` is taken as minutes, as in MS-DIAL
    and NIST.
  - Export writes `RETENTIONTIME` (minutes) from `rt`, and skips the
    same-meaning metadata keys so the value isn't written twice.
- **Builder:** RT is the chosen scan's, or set by hand per row (typed, or a
  click on the EIC trace), or none. `BuildParams.store_rt=False` stores none,
  for imaging runs. The scan's own RT stays in the `rt_min` provenance
  metadata.
- **Search** returns `rt`. The GUI query has an optional RT, and hits show
  Δ RT. RT is **display only**, never a filter: RT shifts between methods
  and columns, and filtering would hide true matches.
- **`Library.load_from_db` now runs the migrations** (they used to run only
  in `create`). The ORM model has `rt`, so an un-migrated library would fail
  with "no such column". Only files that already have an `alembic_version`
  table are migrated, so tables are never created inside another SQLite
  file.

## Consequences

- Opening a library writes to it once, the first time a newer libviz opens
  an older file. This includes MSIAnalyzer as soon as it depends on this
  version: the file must be writable then.
- `merge_from` copies `rt` when the source has it. A source from before the
  migration contributes NULL.
