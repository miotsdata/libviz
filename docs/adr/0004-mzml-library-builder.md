# 4 — Building library spectra from mzML

**Status:** Accepted (P3, 2026-10-28)

## Context

The main reason LibViz exists is to turn measurements of known compounds
(standards, or annotated samples) into library spectra. The input can be:

- DDA: one precursor per MS2 scan, with a narrow isolation window.
- DIA: wide windows holding several precursors.
- Imaging/spatial (MSI): thousands of pixel scans, where RT is meaningless.

The user wants **one spectrum per compound/adduct/CE**: no replicates and no
merged spectra. The user picks the best scan.

## Decision

- **Our own streaming mzML reader** (`core/readers/mzml_reader.py`): lxml
  `iterparse` over `<spectrum>`, cvParams read by accession, with
  `referenceableParamGroup`s resolved. Elements are freed after use, so
  memory stays flat. **Peak arrays are decoded only for scans that match a
  target.** pyteomics' mzML reader would add `psims` as a dependency and
  decodes everything. Measured on a real 130 MB MSI file (15.5k spectra,
  12.4k MS2): a full scan for a target list takes about 1 s.
  - zlib/none compression with 32/64-bit floats is supported. MS-Numpress is
    rejected with a message to reconvert the file.
  - Profile-mode MS2 is rejected: library spectra must be centroided.
- **Matching** (`core/builder.find_candidates`) compares a sorted array of
  target-ion m/z values against each scan using binary search:
  - If the isolation window is narrower than `dia_min_width` (default 3 m/z),
    the scan is DDA. Its selected-ion m/z must be within `ppm` of the ion.
  - Otherwise it is DIA: every target ion inside the window matches, and the
    candidate is flagged **multiplexed** (it may contain other compounds'
    fragments). The CLI skips multiplexed candidates unless
    `--include-multiplexed` is given. The GUI marks them for review and has
    "Reject multiplexed".
  - Polarity must agree with the adduct's charge.
  - An RT window filters scans only when the target list gives one (`rt`
    ± 0.5 min, or `rt_min`/`rt_max`).
- **Adduct m/z** = `(n·M + Δatoms − z·mₑ) / |z|` (`mass_utils.adduct_mz`).
  `infer_precursor_delta` sums *atom* masses, so the electron correction is
  applied here. Without it, [M+H]+ is about 3 ppm off.
- **Groups.** One per (target, adduct, CE), holding its candidates sorted
  best first by `rank_by` (precursor intensity, falling back to TIC; or TIC;
  or number of peaks). The first candidate is pre-chosen. A target ion with
  no MS2 still gets a row ("missing"), so gaps are visible.
- **Peak processing** (per candidate, before ranking):
  - drop zero peaks and peaks below `min_relative_intensity` of the base peak
  - optionally remove the precursor region (≥ precursor − 0.5)
  - optionally normalise the base peak to 1000
  - candidates with fewer than `min_peaks` peaks are dropped
- **Commit** (`builder.commit`) runs in one transaction:
  - Compounds are matched by InChIKey. Missing SMILES/PubChem are filled in.
  - Adduct types are created if new.
  - The stored precursor is the **theoretical** ion m/z. The observed m/z,
    ppm error, file, scan id, RT, isolation window and multiplexed flag go
    into `spectrum_metadata`.
  - If a spectrum already exists for the same compound/adduct/polarity/CE,
    it is skipped or replaced (user's choice; `builder.conflicts` counts them
    beforehand). The "one per key" rule is enforced here, **not in the
    schema**: imported MSP libraries (MoNA…) legitimately contain several
    spectra per key from different instruments.
- **Candidates are kept in RAM** (float64 arrays). For realistic target lists
  that's MBs. The `ponytail:` note in `find_candidates` marks where to spill
  to SQLite if it ever isn't.

## GUI

`Builder` bridge plus `BuilderPage.qml` (Library › Build from mzML…, Ctrl+B):

1. **Setup:** target list (parse errors are all listed at once), mzML files,
   and parameters.
2. **Find spectra:** runs on a worker with progress across all files.
3. **Review:**
   - One row per compound/adduct/CE, with a status: ok / multiplexed /
     missing / not added. Rows can be filtered.
   - The candidate scans for the selected row, and a mirror plot: the
     previewed scan on top, the chosen scan below.
   - "Use this scan" (or double-click), "Don't add", "Best for all".
   - Rows are a `DictListModel` updated in place, so choosing doesn't reset
     the scroll position.
4. **Add to library:** any open library or a new one. The dialog shows the
   conflict count and offers replace or keep.

The same pipeline runs headless with `libviz build`.
