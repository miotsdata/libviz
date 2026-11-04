import numpy as np
from PySide6.QtCore import Property, QObject, Signal, Slot

from libviz.core.readers.mzml_reader import read_scan
from libviz.core.similarity import parse_peak_list
from libviz.gui.inspector_bridge import parse_float
from libviz.gui.library_bridge import LibraryBridge, to_local_path
from libviz.gui.worker import start_task


def scaled(mz, intensity, sign: float = 1.0) -> list:
    """[[mz, y], ...] with the base peak at ±1000 (mirror plots)."""
    intensity = np.asarray(intensity, dtype=float)
    if not len(intensity) or intensity.max() <= 0:
        return []
    return np.column_stack([np.asarray(mz, dtype=float), intensity / intensity.max() * 1000.0 * sign]).tolist()


def peaks_text(mz, intensity) -> str:
    return "\n".join(f"{m:.5f}\t{i:g}" for m, i in zip(mz, intensity))


class SearchBridge(QObject):
    """Spectral search of a query spectrum (pasted peaks, a library spectrum
    or an mzML scan) against every open library (ADR 6)."""

    queryChanged = Signal()
    runningChanged = Signal()
    resultsChanged = Signal()
    selectionChanged = Signal()
    errorOccurred = Signal(str)

    def __init__(self, libraries: LibraryBridge, parent=None):
        super().__init__(parent)
        self._libraries = libraries
        self._query = {"peaks": "", "precursor": "", "polarity": "", "title": "", "rt": ""}
        self._running = False
        self._results: list[dict] = []
        self._selected = -1
        self._hit: dict = {}
        self._request = 0

    # --- query --------------------------------------------------------------

    @Property("QVariantMap", notify=queryChanged)
    def query(self) -> dict:
        return self._query

    def _set_query(self, peaks: str, precursor, polarity: str, title: str, rt: float | None = None):
        self._query = {"peaks": peaks, "precursor": "" if precursor is None else f"{precursor:.5f}",
                       "polarity": polarity or "", "title": title, "rt": "" if rt is None else f"{rt:.3f}"}
        self.queryChanged.emit()
        # A new query starts clean: old hits would look like its results, and
        # a search still running for the old query is dropped.
        self._request += 1
        self._running = False
        self._results, self._selected, self._hit = [], -1, {}
        self.runningChanged.emit()
        self.resultsChanged.emit()
        self.selectionChanged.emit()

    @Slot(str, str, str)
    def setQuery(self, peaks: str, precursor: str, polarity: str):
        self._query = {**self._query, "peaks": peaks, "precursor": precursor, "polarity": polarity}

    @Slot("QVariantMap", str)
    def useSpectrum(self, spectrum: dict, name: str):
        """Query = a library spectrum (the inspector's selection)."""
        if not spectrum:
            return
        self._set_query(peaks_text(spectrum["mz"], spectrum["intensity"]), spectrum["precursor_mz"],
                        spectrum.get("polarity", ""), f"{name} {spectrum.get('adduct', '')} CE {spectrum.get('collision_energy')}",
                        spectrum.get("rt"))
        self._exclude = spectrum.get("id")

    @Slot(str, str)
    def loadScan(self, url: str, scan: str):
        path = to_local_path(url)

        def loaded(s):
            self._set_query(peaks_text(s.mz, s.intensity), s.precursor_mz, s.polarity or "",
                            f"{s.file} {s.scan_id.split()[-1] if s.scan_id else ''}", s.rt_min)
            self._exclude = None
        start_task(self, read_scan, path, scan, on_success=loaded, on_error=self.errorOccurred)

    # --- search -------------------------------------------------------------

    @Property(bool, notify=runningChanged)
    def running(self) -> bool:
        return self._running

    @Slot(str, str, str, str, str, str, str, str)
    def search(self, peaks: str, precursor: str, polarity: str, ppm: str, analog_window: str,
               tolerance: str, min_matched: str, rt: str = ""):
        """``rt`` (minutes, optional) is only displayed: each hit gets its Δ RT."""
        mz, intensity = parse_peak_list(peaks)
        precursor_mz = parse_float(precursor)
        if not len(mz):
            self.errorOccurred.emit("Enter the query peaks: one 'm/z intensity' pair per line.")
            return
        if precursor_mz is None or precursor_mz <= 0:
            self.errorOccurred.emit("Enter the query's precursor m/z.")
            return
        libraries = list(self._libraries.manager.libraries.values())
        if not libraries:
            self.errorOccurred.emit("Open at least one library to search.")
            return
        self._query = {**self._query, "peaks": peaks, "precursor": precursor, "polarity": polarity, "rt": rt}
        query_rt = parse_float(rt)
        options = dict(precursor_mz=precursor_mz, polarity=polarity or None,
                       precursor_ppm=parse_float(ppm) or 10.0, analog_window=parse_float(analog_window) or 0.0,
                       fragment_tolerance=parse_float(tolerance) or 0.01,
                       min_matched=int(parse_float(min_matched) or 1), top=50)
        exclude = getattr(self, "_exclude", None)
        self._request += 1
        request = self._request

        def run():
            hits = []
            for lib in libraries:
                for h in lib.search_spectrum(mz, intensity, exclude_spectrum_id=exclude, **options):
                    delta_rt = h["rt"] - query_rt if h["rt"] is not None and query_rt is not None else None
                    hits.append({**h, "library": lib.name, "libraryPath": str(lib.path), "delta_rt": delta_rt})
            hits.sort(key=lambda h: h["score"], reverse=True)
            return hits[:50]

        def done(hits):
            if request != self._request:
                return
            self._running = False
            self.runningChanged.emit()
            self._results = hits
            self._query_peaks = (mz, intensity)
            self.resultsChanged.emit()
            self.selectHit(0 if hits else -1)

        def failed(message):
            self._running = False
            self.runningChanged.emit()
            self.errorOccurred.emit(message)
        self._running = True
        self.runningChanged.emit()
        start_task(self, run, on_success=done, on_error=failed)

    @Property(list, notify=resultsChanged)
    def results(self) -> list:
        return [{**h, "index": i} for i, h in enumerate(self._results)]

    @Property(int, notify=selectionChanged)
    def selectedHit(self) -> int:
        return self._selected

    @Property("QVariantMap", notify=selectionChanged)
    def mirror(self) -> dict:
        """Query on top, selected hit below (both base peak 1000)."""
        if not self._hit:
            return {}
        mz, intensity = self._query_peaks
        return {"query": scaled(mz, intensity), "hit": scaled(self._hit["mz"], self._hit["intensity"], -1.0),
                "title": f"{self._results[self._selected]['name']} · cosine "
                         f"{self._results[self._selected]['score']:.3f}"}

    @Slot(int)
    def selectHit(self, index: int):
        self._selected = index
        self._hit = {}
        self.selectionChanged.emit()
        if not 0 <= index < len(self._results):
            return
        hit = self._results[index]
        lib = self._libraries.manager.library(hit["libraryPath"])
        if lib is None:
            return

        def loaded(spectrum):
            if self._selected == index:
                self._hit = spectrum
                self.selectionChanged.emit()
        start_task(self, lib.get_spectrum, hit["spectrum_id"], on_success=loaded, on_error=self.errorOccurred)
