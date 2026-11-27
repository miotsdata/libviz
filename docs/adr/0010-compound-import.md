# 10 — Importing compounds from Excel/CSV, then their spectra

**Status:** Accepted (2026-11-27)

## Context

Labs keep their standards in Excel: one sheet per project, Italian or
English headers, extra columns (RT, concentrations, flags), and compounds
with no real InChIKey (new conjugates, internal standards). The builder's
target list (ADR 4) is a strict CSV: it rejects the whole file for one bad
row, and it mixes compound data with search data (adducts, RT). The user
wants to load **compounds** into a library first, then find their spectra.

## Decision

- **Two steps:**
  1. *Library › Import compounds…* adds compounds (no spectra) to the
     selected library (`core/compound_import.py`).
  2. The builder's *Choose compounds…* turns a library's compounds into
     targets with the default adducts. Commit already matches compounds by
     key, so the spectra land on the imported compounds.
  The builder's CSV target list is kept as it is (the `libviz build` CLI
  uses it).
- **Reading:** xlsx through `pandas.read_excel` (adds `openpyxl`; `.xls` is
  not supported), CSV/TSV/`;` through `csv`. All cells are read as text.
  The header is the first non-empty row; line numbers are the sheet's.
- **Column mapping**, not more aliases: each field (name, formula, mass,
  InChIKey, SMILES, PubChem) gets a column, guessed from English/Italian
  headers and changeable in the dialog. RT and adducts are not compound
  data, so they aren't fields. (A header like `RT min` would also have
  clashed with the target list's `rt_min`, which is a window start.)
- **Rows are checked, never all-or-nothing.** Each row is ok, warning
  (imported) or error (skipped):
  - formula: whitespace and zero-width characters are removed. `D` not
    followed by a lowercase letter is deuterium (`H[2]` for pyteomics), so
    Dy/Db/Ds are untouched. This lives in `mass_utils.calculate_exact_mass`,
    so the builder, Identify and compound editing accept it too.
  - formula and mass: the formula wins. More than 0.01 Da apart is a warning
    (it catches average MW columns and typos). Mass only: used, with a
    warning. Neither: error.
  - the same key twice: the first row is kept, and later ones are errors.
- **Compounds without a valid InChIKey are accepted.** `compound.inchikey`
  stays `NOT NULL UNIQUE`: it is the identity used by merge, MSP import,
  commit and MSIAnalyzer. The cell's value becomes the key (`TRYPT-CA`), or
  `NOKEY:<name>` when the cell is empty. There is no migration, and the
  matching code keeps working.
  - A new quality check, `bad_inchikey` (SQLite `GLOB` on the 14-10-1
    pattern), lists them in the overview with *Show*.
  - MSP export omits `INCHIKEY` for them.
  - Builder `identify` accepts any non-empty key (the builder's CSV target
    list still requires real ones).
- **Import into a library** happens in one transaction. An existing
  compound (same key) is kept, and its missing SMILES/PubChem are filled
  in. Name and formula are never overwritten.

## Consequences

- Two libraries that both use a stand-in key (e.g. `GLY-CA`) merge those
  compounds as one. That is right when the stand-in names the same
  compound, which is how they are used.
- Not done: a CLI `import-compounds` command, the second name column (e.g.
  `Sigla`) as a synonym (the schema has no field for it), several tables
  side by side in one sheet, `.xls`.
