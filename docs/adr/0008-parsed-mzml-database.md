# 8 — Parsed mzML database (shared with MSIAnalyzer) and EIC

**Status:** Accepted (2026-11-04)

## Context

The builder re-read every mzML (XML, base64, zlib) on each *Find spectra*.
That was acceptable for one target-list run (ADR 4). It isn't for exploring
by hand (an m/z, look, another m/z), or for an EIC, which needs every MS1
scan decoded. MSIAnalyzer already stores each run as a "raw" SQLite database
(`ms1_scans`/`ms2_scans`). MSIAnalyzer depends on libviz, not the other way
round, so shared code has to live in libviz.

## Decision

- **`core/readers/mzml_db.py`** writes MSIAnalyzer's raw schema: `metadata`,
  `commands`, `ms1_scans`, `ms2_scans`; RT in seconds; peaks as zlib float32
  blobs rounded to 4 decimals. Both tools read each other's files.
  Additions that MSIAnalyzer ignores:
  - a `native_id` column (the mzML spectrum id, kept for provenance)
  - `metadata` keys `source_size`, `source_mtime_ns`,
    `libviz_format_version` and `ms1_profile_skipped`
- **Parsing reuses libviz's lxml reader** (`mzml_reader.iter_spectra`), not
  MSIAnalyzer's regex parser. That fixes, for the shared format:
  - non-Thermo native ids: `scan_id` falls back to the 1-based spectrum
    index when there is no unique `scan=N` (e.g. Waters `function=… scan=N`).
    An integer key with a string inserted, or a silent overwrite, are not
    possible.
  - referenceable param groups are resolved
  - MS-Numpress raises instead of storing empty arrays
  - the parent MS1 scan is resolved through the native id
- **Profile-mode MS1 is skipped** (counted in `ms1_profile_skipped`), and the
  GUI says that this is why there is no EIC. Profile MS2 still raises, as in
  ADR 4. MSIAnalyzer rejects profile MS1 before parsing, so its use is
  unaffected.
- **Cache:**
  - The DB is `run.mzML.db` next to the mzML, or in the user cache folder
    (`$LOCALAPPDATA`/`$XDG_CACHE_HOME`/`~/.cache`) under
    `libviz/parsed/run.mzML.<hash>.db` if the folder is not writable.
  - It is re-parsed when the mzML's size or mtime, or `FORMAT_VERSION`,
    changes.
  - It is written to `*.part` without a journal, then renamed: a crash
    leaves no half database. A cache can always be rebuilt, so ADR 1's
    durability rules don't apply to the file under construction.
- **Builder:** `find_candidates` matches MS2 scans from the DB
  (`iter_ms2_db`, same `keep` contract as `iter_ms2`). Peaks are read only
  for matches.
- **EIC** (`mzml_db.eic`): for each MS1 scan whose m/z range covers the ion,
  the intensity within ± ppm is summed. The review page shows it per file
  above the spectrum, with the row's MS2 candidates as sticks at their RT
  (the chosen one in red). Clicking one previews that scan. The plot is
  `StickPlot` (one stick per MS1 scan), with no new plot component.

## Measurements

- Real 1.9 GB DDA file (48k MS2, profile MS1):
  - parse: 8.3 s once, DB 26 MB
  - MS2 matching pass: 0.17 s, against 4.3 s from the XML
- Synthetic LC run, 3,000 centroided MS1 scans × 1,000 peaks: EIC in 0.11 s.

## Consequences

- MSIAnalyzer can switch to `libviz.core.readers.mzml_db` for parsing and
  drop its own parser. Its pixel tables stay its own, added after parsing.
- Peaks pass through float32 (≈0.06 ppm at m/z 1000), which is below any
  library tolerance.
- The cached DB is roughly MS1-sized, and much larger for centroided
  MS1-heavy files. Delete `*.mzML.db` to reclaim space; they are rebuilt on
  demand.
