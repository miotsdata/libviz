# 1 — SQLite durability, temp libraries and library keys

**Status:** Accepted (P0, 2026-10-28)

## Context

Every connection a `Library` opened ran `journal_mode=MEMORY` and
`synchronous=OFF`, including connections to a `.db` the user had saved and
keeps editing. A crash or power loss during a write can corrupt that file. The
pragmas were only there to make bulk MSP import fast.

`save_as_db` copied the temp file to its destination but kept the engine
bound to the temp path, so every later edit went to the temp file and was lost.
The temp file was never deleted either.

`LibraryManager` stored libraries under a `Path`, while the bridge passed
plain strings from QML, so `selectLibrary`/`unloadLibrary` could silently miss.

## Decision

- **Fast pragmas only for disposable DBs.** `Library(..., fast_writes=True)`
  (used by `load_from_msp`, which imports into a temp file) keeps
  `MEMORY`/`OFF`. Every other library uses SQLite defaults
  (rollback journal `DELETE`, `synchronous=FULL`). `foreign_keys=ON` everywhere.
- **No WAL.** Libraries are shared on network drives (SMB/CIFS), where WAL's
  shared-memory index is unsafe. `save_as_db` already avoids `backup()` for
  the same reason.
- **`save_as_db` rebinds the engine** to the saved file with safe pragmas and
  deletes the old temp file. `Library.close()` disposes the engine and deletes
  the file if the library is still temp. `LibraryManager.unload_library` calls it.
- **One key form:** `library_key(path) = str(Path(path).resolve())`.
  `LibraryManager` methods return the key, and `save_as_db` re-keys the
  library under its new path.
- `n_compounds`/`n_spectra` are live `COUNT(*)` queries instead of a
  snapshot taken at load time, which went stale after `add_spectra`.

## Consequences

- Writes to saved libraries are slower (one fsync per commit). Bulk writes
  (MSP import, mzML builder) go through a temp library and are then saved, so
  they stay fast.
- `Library.loadFromMSP` was renamed to `load_from_msp`. MSIAnalyzer never
  called it. The surface MSIAnalyzer does use is pinned by
  `tests/unit/test_public_api.py`.
