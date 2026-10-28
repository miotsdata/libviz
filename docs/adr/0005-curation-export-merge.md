# 5 — Curation: edit, delete, MSP export, merge

**Status:** Accepted (P4, 2026-10-28)

## Decision

- **Editing** goes through `Library` methods, each one transaction:
  - `update_compound` changes name, formula (which recomputes the exact
    mass), SMILES and PubChem CID. **The InChIKey is not editable.** It is
    the compound's identity (unique, used for merge and builder matching),
    so a wrong InChIKey means deleting the compound and adding it again.
  - `delete_spectra` keeps the compound. `delete_compounds` cascades to the
    compound's spectra and metadata.
  - `set_spectrum_metadata` / `delete_spectrum_metadata` act on key/value
    fields. A rename in the GUI is delete + set.
  - Editing a spectrum's peaks, adduct or CE isn't offered (YAGNI): delete
    it and rebuild it instead.
- In the GUI, every write is a `Task` followed by
  `Libraries.libraryContentChanged(key)` and a recount. The inspector
  reloads the table and the selected compound/spectrum. Compound and
  spectrum loads carry a request counter, so with fast clicking only the
  newest answer is applied. Deletes ask for confirmation. **There is no
  undo**: a saved library is edited in place, and *Save as* first gives a
  copy.
- **MSP export** (`core/writers/msp_writer.py`) streams 2000 spectra at a
  time by id (keyset pagination, not OFFSET). It writes NAME, PRECURSORMZ,
  PRECURSORTYPE, FORMULA, INCHIKEY, SMILES, PUBCHEM, EXACTMASS, IONMODE,
  COLLISIONENERGY, then every metadata field (made single-line; reserved
  keys skipped), then the peaks. The file is written as `.tmp` and renamed
  into place. Exporting and re-importing gives the same compounds, spectra,
  peaks and metadata (tested).
- **Merge** (`Library.merge_from`) is done entirely in SQL with `ATTACH`:
  - Compounds are matched by InChIKey, and the existing compound wins.
  - Adduct types are matched by formula.
  - A spectrum is skipped when it is identical (same compound, adduct,
    polarity, CE and peak hash). This is an explicit `NOT EXISTS … polarity
    IS …`, because the UNIQUE constraint treats NULL polarities as distinct
    and would let them through (found by a test).
  - Metadata is copied only for newly inserted spectra.
  - Merging is idempotent.
- Timings with 500k spectra (`pytest -m slow`): export 5 s, merge 6 s.

## Consequences

- MSP files without polarity can still produce duplicate rows when the
  *same* file is imported once; the same NULL-distinct rule applies. It
  doesn't matter in practice, and merge cleans it up.
- CLI: `libviz export`, `libviz merge TARGET SOURCES…`.
