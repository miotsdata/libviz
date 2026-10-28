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

## Building a library from mzML

*Library › Build from mzML…* (Ctrl+B), or the button on the start page.

1. **Target list:** a CSV, TSV or `;`-separated table with a header row.

   | column | required | notes |
   |---|---|---|
   | `name` | yes | |
   | `formula` | yes | neutral molecular formula, used for the exact mass |
   | `inchikey` | yes | identifies the compound in the library |
   | `smiles`, `pubchem_id` | no | stored with the compound |
   | `adducts` | no | e.g. `[M+H]+\|[M+Na]+`; otherwise the default adducts |
   | `rt` or `rt_min`/`rt_max` | no | minutes; `rt` means ± 0.5 min. Leave empty for DIA/imaging or when unknown. |

   Every problem in the file (bad formula, malformed InChIKey, unknown
   adduct, duplicate compound) is listed at once.
2. **mzML files:** centroided MS2 (convert with msconvert,
   `peakPicking true 1-`). DDA, DIA and imaging runs all work.
3. **Parameters:**
   - precursor tolerance (ppm)
   - default adducts per polarity
   - the isolation width from which a scan counts as DIA
   - minimum peak intensity (% of the base peak) and minimum number of peaks
   - optional precursor removal and normalisation
   - how scans are ranked
4. **Find spectra**, then **review**:
   - There is one row per compound/adduct/collision energy.
   - The best-ranked scan is pre-chosen. Click another candidate to compare
     it with the chosen one (mirror plot), then *Use this scan*, or
     double-click it.
   - *Don't add* leaves a row out. *Missing* means no MS2 matched.
     *Multiplexed* means a DIA window that may contain other compounds;
     review those, or *Reject multiplexed*.
5. **Add to library:**
   - Pick an open library or create a new one.
   - If the library already has a spectrum for the same compound, adduct,
     polarity and CE, choose whether to keep it or replace it.
   - Provenance (file, scan, RT, observed m/z and ppm error) is saved in the
     spectrum's metadata.

## Command line

```bash
libviz convert MoNA.msp -o mona.db              # MSP -> library
libviz build targets.csv run1.mzML run2.mzML -o standards.db --ppm 5
libviz build targets.csv dia.mzML -o lib.db --include-multiplexed --replace
libviz info standards.db
```

`libviz build` keeps the best-ranked scan for every compound/adduct/CE. It
takes the same parameters as the GUI (`libviz build -h`).
