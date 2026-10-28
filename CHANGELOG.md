# Changelog

## Unreleased

### Fixed
- Saved libraries no longer use `synchronous=OFF`/`journal_mode=MEMORY` (risk of corruption on crash) — ADR 1.
- Edits after "Save as" went to the temp file and were lost.
- Temp MSP-import databases are deleted when the library is saved or closed.
- Selecting/unloading a library from the GUI could silently fail (str vs Path keys).
- Library counts were stale after adding spectra.

### Changed
- `Library.loadFromMSP` → `Library.load_from_msp`; an imported MSP library is named after the file.
- GUI extra depends on `pyside6-essentials`/`pyside6-addons` ≥ 6.12 (no PyQt6, no WebEngine).
