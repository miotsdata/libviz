# User guide

## Libraries

A LibViz library is a single SQLite `.db` file. Open as many as you like.
They are listed in the sidebar; click one to inspect it, or right-click it
to close it.

| Action | Menu | Notes |
|---|---|---|
| New empty library | File › New library… (Ctrl+N) | Created at the chosen path. |
| Open a library | File › Open library… (Ctrl+O), File › Open recent | |
| Import an MSP file | File › Import MSP… (Ctrl+I) | The import is **unsaved** until you use *Save as*. A summary shows how many entries were imported and why the rest were skipped (no InChIKey, bad precursor m/z, unknown adduct, duplicate). |
| Save as | File › Save as… (Ctrl+Shift+S) | Copies the library to a new `.db`; later edits go there. |
| Rename | Library › Rename… | The name is stored inside the file. |
| Export as MSP | File › Export as MSP… (Ctrl+E) | Every spectrum, with its metadata. |
| Merge | Library › Merge another library into this… | Copies compounds and spectra from a `.db`; identical spectra are skipped. |
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

## Overview and quality checks

The **Overview** tab of a library shows:

- the number of compounds, spectra, adducts and collision energies
- distributions by polarity, adduct, CE and peaks per spectrum
- a precursor m/z histogram
- **Quality checks**: compounds without spectra or SMILES, spectra with
  ≤ 2 peaks or without polarity, and duplicate spectra. *Show* filters the
  compound table to the affected compounds. Clear the filter with ✕ or
  *Clear*.

## Comparing spectra

In the spectra list, right-click a spectrum and choose *Compare with the
selected spectrum*. The two are drawn as a mirror plot with their cosine
similarity and the number of matched peaks.

## Spectral search

*Library › Spectral search…* (Ctrl+F), or *Search similar* above a spectrum.

- **Query:** paste peaks (`m/z intensity` per line), *Search similar* from
  the inspector, or *Load mzML scan…* (file + scan number). The precursor
  m/z is required.
- Every open library is searched:
  - Spectra with a precursor within the ppm tolerance are scored by cosine
    similarity.
  - *Analog search* instead uses every precursor within ± the window (Da)
    and scores with the modified cosine, which also matches fragments
    shifted by the precursor difference.
- Click a hit to see the query vs library mirror plot. Double-click it to
  open the compound in its library.

## Curating

- **Edit a compound:** right-click it in the table, or use the **⋯** button
  next to its name, then *Edit compound…*. You can change the name,
  formula, SMILES and PubChem CID. The InChIKey identifies the compound and
  cannot be edited.
- **Delete:**
  - *Delete compound…* removes the compound and all its spectra.
  - Right-click a spectrum in the spectra list and choose *Delete
    spectrum…* to remove just that spectrum.
- **Spectrum metadata:** *Add field…* adds one. Use ✎ to edit a field and
  ✕ to delete it.
- **Export one compound:** *Export as MSP…* in the compound menu.

Changes are written to the library immediately and can't be undone. Use
*Save as* first if you want to keep the original.

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
libviz export standards.db -o standards.msp
libviz merge all.db standards.db mona.db         # all.db is created if missing
libviz info standards.db
```

`libviz build` keeps the best-ranked scan for every compound/adduct/CE. It
takes the same parameters as the GUI (`libviz build -h`).
