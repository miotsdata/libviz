# 6 — Similarity, spectral search, compare and library overview

**Status:** Accepted (P5, 2026-10-28)

## Decision

- **`core/similarity.py`** has a greedy cosine and a modified cosine,
  equivalent to matchms' `CosineGreedy`/`ModifiedCosine`:
  - Peaks pair within an absolute tolerance (Da, default 0.01). Each peak is
    used once, highest weight products first.
  - Weights are `mz^mz_power · intensity^intensity_power` (defaults 0 / 1).
  - Modified cosine also pairs peaks shifted by the precursor difference,
    which is what analog search needs.
  - Pure numpy with no DB access, so MSIAnalyzer can import it
    (**reminder:** switch `msianalyzer/core/annotation/spectral_match.py`
    to it; not done now, at the user's request).
  - `parse_peak_list` accepts pasted peaks (`m/z intensity` lines or
    MoNA's `mz:int …`).
- **Spectral search** (`Library.search_spectrum`):
  - Candidates come from the indexed `precursor_mz` column: ± ppm for a
    normal search, ± *window* Da (modified cosine) for analog search. Then
    everything is scored in Python.
  - A search without a precursor is not offered. Scoring every spectrum of
    a 500k library in Python would take minutes, and every real query
    (library spectrum, mzML scan) has a precursor.
  - The GUI's `Search` page queries **all open libraries**. The query can be
    pasted peaks, the inspector's spectrum ("Search similar", which
    excludes the spectrum itself) or an mzML scan by number
    (`mzml_reader.read_scan`). The page shows a mirror plot of query vs hit,
    and double-clicking a hit opens it in the inspector.
- **Compare:** in the inspector's spectra list, right-click → *Compare with
  the selected spectrum*. This draws a mirror plot (both base peaks at 1000)
  with the cosine and the number of matched peaks.
- **Overview tab** (`Library.overview`, SQL aggregates):
  - Headline counts.
  - Spectra by polarity, adduct, CE and peaks per spectrum, as single-hue
    bars. These are magnitudes, not identities, so there's no categorical
    palette and no legend. Values are shown next to each bar.
  - A precursor m/z histogram with hover values.
  - **Quality checks** (`Library.ISSUES`): no spectra, no SMILES, a
    spectrum with ≤ 2 peaks, a spectrum without polarity, duplicate
    spectra. Each shows an icon and a count, so color is never the only
    signal. *Show* turns the check into a compound-table filter
    (`issue=…`), which makes QC actionable.
  - It loads only when the tab is opened: 1.6 s at 500k spectra (the
    other QC counts take about 0.3 s each).
- The main window switches pages with `page` (`""` = library/welcome,
  `"builder"`, `"search"`). The builder and search keep their state in their
  bridges while hidden.

## Measurements (500k spectra, `pytest -m slow`)

Overview 1.6 s · issue filters 0.3 s · spectral search (±20 ppm) 2 ms.
