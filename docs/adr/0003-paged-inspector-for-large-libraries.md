# 3 — Paged inspector for large libraries

**Status:** Accepted (P2, 2026-10-28)

## Context

Libraries can be MoNA-sized: 100k+ compounds and 500k+ spectra. Loading
every compound into QML (a JS array or a fully populated model) takes seconds
and hundreds of MB, and it blocks the GUI thread.

## Decision

- **Filtering, sorting and paging run in SQL** (`Library.search_compounds`,
  `count_compounds`, `filter_options`, `get_compound_spectra`, `get_spectrum`):
  - Text search is a case-insensitive name substring, an InChIKey prefix, or
    an exact formula. LIKE wildcards in the input are escaped.
  - Mass search uses ± ppm on the neutral exact mass **or** on any spectrum's
    precursor m/z, because users type either one.
  - Polarity/adduct/CE filters are a single `EXISTS` on `spectrum`.
  - The number of spectra per compound is a correlated subquery, computed for
    the page rows only. Sorting by it isn't offered.
- **`CompoundTableModel` is virtual.** `rowCount` is the full match count
  (one `COUNT`), so the scrollbar is accurate. Pages of 200 rows are fetched
  on a `Task` the first time the view asks for them, and rows show blank
  until they arrive. At most 50 pages are cached; the pages furthest from
  the newest are evicted. Each filter, sort or library change bumps a
  generation counter, and results or errors from an older generation are
  dropped. That also covers a library closed while a page is loading.
- The spectrum panel only loads the selected compound's spectrum list and
  one spectrum's peaks at a time.
- Peak arrays cross into QML as plain lists (not numpy), and the plot is
  MSIAnalyzer's `StickPlot` (Qt Graphs, themed, wheel-zoom on m/z).

## Measurements

`tests/unit/test_library_scale.py` (`pytest -m slow`), with 100k compounds and
500k spectra on a laptop SSD: count 7 ms, first page 2 ms, page at offset 90k
6 ms, text search 36 ms, polarity count 170 ms, mass search 340 ms (the
`OR` across two indexes can't use either). The test fails if any query
takes longer than 1 s.

## Consequences

- Name sorting is SQLite `NOCASE` lexical order ("compound 10" before
  "compound 2"). That's acceptable for now.
- If mass search turns out to be too slow on real data, run it as a union of
  two indexed id queries.
