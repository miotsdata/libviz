# Changelog

## 0.2.0 — 2026-10-28

### Fixed
- Saved libraries no longer use `synchronous=OFF`/`journal_mode=MEMORY` (risk of corruption on crash) — ADR 1.
- Edits after "Save as" went to the temp file and were lost.
- Temp MSP-import databases are deleted when the library is saved or closed.
- Selecting/unloading a library from the GUI could silently fail (str vs Path keys).
- Library counts were stale after adding spectra.

### Added
- New desktop GUI shell (ADR 2): menubar, sidebar of open libraries, status bar with progress, light/dark theme, recent libraries, unsaved-library and quit confirmations. Launch with `libviz-gui`.
- MSP import reports progress.
- Library inspector (ADR 3): search by name/formula/InChIKey or mass ± ppm, polarity/adduct/CE filters, sortable paged compound table that stays fast on 500k-spectrum libraries, spectra list, interactive spectrum plot, compound identifiers and spectrum metadata, copy peaks.
- **Build library spectra from mzML** (ADR 4): target list (CSV/TSV) + DDA/DIA/imaging mzML files → one spectrum per compound/adduct/CE, reviewed and picked in the GUI (mirror-plot comparison) or chosen automatically by `libviz build`; provenance stored as spectrum metadata; skip/replace existing spectra.
- Fast streaming mzML reader (`core/readers/mzml_reader.py`), no new dependency.
- Library overview with quality checks that filter the table; compare two spectra (mirror + cosine); spectral and analog search across open libraries from pasted peaks, a library spectrum or an mzML scan (ADR 6).
- `core/similarity.py`: greedy (modified) cosine, `parse_peak_list`; `Library.search_spectrum`, `Library.overview`, issue filters.
- Curation (ADR 5): edit compounds (name, formula, SMILES, PubChem), delete compounds/spectra, add/edit/delete spectrum metadata.
- Export a library or a single compound as MSP; merge libraries (identical spectra skipped).
- `libviz` command line: `convert`, `build`, `export`, `merge`, `info`.
- `mass_utils.adduct_mz` (electron-corrected adduct m/z).
- `Library.search_compounds`, `count_compounds`, `filter_options`, `get_compound`, `get_compound_spectra`, `get_spectrum`.

### Changed
- `Library.loadFromMSP` → `Library.load_from_msp`; an imported MSP library is named after the file.
- GUI extra depends on `pyside6-essentials`/`pyside6-addons` ≥ 6.12 (no PyQt6, no WebEngine).
