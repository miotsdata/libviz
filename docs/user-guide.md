# User guide

## Libraries

A LibViz library is a single SQLite `.db` file. Open as many as you like.
They are listed in the sidebar; click one to inspect it, or right-click it
to close it.

| Action | Menu | Notes |
|---|---|---|
| New empty library | File › New library… (Ctrl+N) | Created at the chosen path. |
| Open a library | File › Open library… (Ctrl+O), File › Open recent | |
| Import an MSP file | File › Import MSP… (Ctrl+I) | The import is **unsaved** until you use *Save as*. |
| Save as | File › Save as… (Ctrl+Shift+S) | Copies the library to a new `.db`; later edits go there. |
| Rename | Library › Rename… | The name is stored inside the file. |
| Theme | View › Dark theme | Remembered across sessions. |

Closing an unsaved import, or quitting with one open, asks before
discarding it.

## Inspecting a library

- **Filter bar:**
  - Free text matches compound name (substring), InChIKey (prefix) or
    formula (exact).
  - *Mass or m/z* ± *ppm* matches the neutral exact mass or any precursor m/z.
  - Polarity / adduct / CE list only the values used in the library.
- **Compound table:** click a header to sort (click again to reverse).
  Click a row, or use ↑/↓ and PgUp/PgDn, to select a compound. Large
  libraries scroll smoothly because rows load in pages.
- **Spectrum panel:**
  - The selected compound's spectra (adduct, polarity, CE, precursor, number
    of peaks).
  - The spectrum plot: mouse wheel zooms m/z, drag pans, double-click
    resets, hover shows a peak's values. *Copy peaks* copies
    `m/z<TAB>intensity` lines.
  - Compound identifiers (InChIKey, SMILES, PubChem link) and every metadata
    field stored with the spectrum.
