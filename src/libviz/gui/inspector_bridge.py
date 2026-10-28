from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication

from libviz.gui.compound_model import CompoundTableModel
from libviz.core.writers import write_msp
from libviz.gui.library_bridge import LibraryBridge, to_local_path
from libviz.gui.worker import start_task


def parse_float(text: str) -> float | None:
    """A user-typed number ("195.0877", "195,0877", ""); None if not one."""
    try:
        return float(str(text).strip().replace(",", "."))
    except ValueError:
        return None


def peaks_as_text(spectrum: dict) -> str:
    """Tab-separated "m/z<TAB>intensity" lines, ready to paste anywhere."""
    return "\n".join(f"{mz:.4f}\t{i:g}" for mz, i in zip(spectrum.get("mz", []), spectrum.get("intensity", [])))


class InspectorBridge(QObject):
    """Browse the selected library: filtered compound table → spectra of the
    selected compound → one spectrum (peaks + metadata). All reads run on
    workers; a late answer for something no longer selected is dropped."""

    filterOptionsChanged = Signal()
    compoundChanged = Signal()
    spectraChanged = Signal()
    spectrumChanged = Signal()
    errorOccurred = Signal(str)

    def __init__(self, libraries: LibraryBridge, parent=None):
        super().__init__(parent)
        self._libraries = libraries
        self._model = CompoundTableModel(self)
        self._model.errorOccurred.connect(self.errorOccurred)
        self._key = ""
        self._filter_options = {"polarities": [], "adducts": [], "collision_energies": []}
        self._compound: dict = {}
        self._spectra: list = []
        self._spectrum: dict = {}
        # Only the newest compound/spectrum request is applied (fast clicking).
        self._compound_request = 0
        self._spectrum_request = 0
        libraries.selectedChanged.connect(self._on_selected)
        libraries.libraryContentChanged.connect(self._on_content_changed)

    def _error_for(self, key: str):
        """Error handler that stays quiet once ``key`` is no longer shown
        (a library closed mid-query is not an error worth a dialog)."""
        return lambda message: key == self._key and self.errorOccurred.emit(message)

    @property
    def _lib(self):
        return self._libraries.manager.library(self._key) if self._key else None

    def _on_selected(self):
        key = self._libraries.selectedKey
        if key == self._key:
            return
        self._key = key
        self._model.set_library(self._lib)
        self._clear_selection()
        self._load_filter_options()

    def _on_content_changed(self, key: str):
        if key != self._key:
            return
        self._model.reload()
        self._load_filter_options()
        if self._compound:
            self._load_compound(self._compound["id"], keep_spectrum=True)

    def _clear_selection(self):
        self._compound, self._spectra, self._spectrum = {}, [], {}
        self.compoundChanged.emit()
        self.spectraChanged.emit()
        self.spectrumChanged.emit()

    def _load_filter_options(self):
        lib, key = self._lib, self._key
        if lib is None:
            return

        def loaded(options):
            if key == self._key:
                self._filter_options = options
                self.filterOptionsChanged.emit()
        start_task(self, lib.filter_options, on_success=loaded, on_error=self._error_for(key))

    def _load_compound(self, compound_id: int, keep_spectrum: bool = False):
        lib, key = self._lib, self._key
        if lib is None:
            return

        self._compound_request += 1
        request = self._compound_request

        def load():
            return lib.get_compound(compound_id), lib.get_compound_spectra(compound_id)

        def loaded(result):
            if key != self._key or request != self._compound_request:
                return
            self._compound, self._spectra = result
            self.compoundChanged.emit()
            self.spectraChanged.emit()
            ids = [s["id"] for s in self._spectra]
            if keep_spectrum and self._spectrum.get("id") in ids:
                self.selectSpectrum(self._spectrum["id"])
            elif ids:
                self.selectSpectrum(ids[0])
            else:
                self._spectrum = {}
                self.spectrumChanged.emit()
        start_task(self, load, on_success=loaded, on_error=self._error_for(key))

    # --- QML API ----------------------------------------------------------------

    @Property(QObject, constant=True)
    def compounds(self) -> CompoundTableModel:
        return self._model

    @Property("QVariantMap", notify=filterOptionsChanged)
    def filterOptions(self) -> dict:
        return self._filter_options

    @Property("QVariantMap", notify=compoundChanged)
    def compound(self) -> dict:
        return self._compound

    @Property(list, notify=spectraChanged)
    def spectra(self) -> list:
        return self._spectra

    @Property("QVariantMap", notify=spectrumChanged)
    def spectrum(self) -> dict:
        return self._spectrum

    @Slot(str, str, str, str, str, str)
    def setFilters(self, text: str, mass: str, ppm: str, polarity: str, adduct: str, collision_energy: str):
        """Empty strings mean "any". ``mass`` is a neutral mass or m/z."""
        self._model.set_filters({
            "text": text,
            "mass": parse_float(mass),
            "ppm": parse_float(ppm) or 10.0,
            "polarity": polarity or None,
            "adduct": adduct or None,
            "collision_energy": parse_float(collision_energy),
        })

    @Slot(int)
    def selectCompoundRow(self, row: int):
        data = self._model.row_data(row)
        if data is not None:
            self._load_compound(data["id"])

    @Slot(int)
    def selectCompound(self, compound_id: int):
        self._load_compound(compound_id)

    @Slot(int)
    def selectSpectrum(self, spectrum_id: int):
        lib, key = self._lib, self._key
        if lib is None:
            return

        self._spectrum_request += 1
        request = self._spectrum_request

        def loaded(spectrum):
            if key == self._key and request == self._spectrum_request:
                self._spectrum = spectrum
                self.spectrumChanged.emit()
        start_task(self, lib.get_spectrum, spectrum_id, on_success=loaded, on_error=self._error_for(key))

    # --- editing (ADR 5) ----------------------------------------------------

    def _write(self, fn, *args, then=None, **kwargs):
        """Run a library write; then tell everyone the library changed."""
        key = self._key
        if not key:
            return

        def done(_):
            if then is not None:
                then()
            self._libraries.libraryContentChanged.emit(key)
            self._libraries.refresh(key)
        start_task(self, fn, *args, on_success=done, on_error=self._error_for(key), **kwargs)

    @Slot(str, str, str, str)
    def updateCompound(self, name: str, formula: str, smiles: str, pubchem_id: str):
        if self._compound and self._lib is not None:
            pubchem = pubchem_id.strip()
            if pubchem and not pubchem.isdigit():
                self.errorOccurred.emit(f"PubChem CID must be a number, not {pubchem!r}")
                return
            self._write(self._lib.update_compound, self._compound["id"], name=name, formula=formula,
                        smiles=smiles, pubchem_id=int(pubchem) if pubchem else 0)

    @Slot()
    def deleteCompound(self):
        if self._compound and self._lib is not None:
            self._write(self._lib.delete_compounds, [self._compound["id"]], then=self._clear_selection)

    @Slot(int)
    def deleteSpectrum(self, spectrum_id: int):
        if self._lib is not None:
            def forget():
                if self._spectrum.get("id") == spectrum_id:
                    self._spectrum = {}
            self._write(self._lib.delete_spectra, [spectrum_id], then=forget)

    @Slot(str, str)
    def setMetadata(self, key: str, value: str):
        if self._spectrum and self._lib is not None:
            self._write(self._lib.set_spectrum_metadata, self._spectrum["id"], key, value)

    @Slot(str)
    def deleteMetadata(self, key: str):
        if self._spectrum and self._lib is not None:
            self._write(self._lib.delete_spectrum_metadata, self._spectrum["id"], key)

    @Slot(str)
    def exportCompoundMsp(self, url: str):
        """Export the selected compound's spectra as MSP."""
        lib, key = self._lib, self._key
        if not self._compound or lib is None:
            return
        path = to_local_path(url)
        if not path.lower().endswith(".msp"):
            path += ".msp"
        start_task(self, write_msp, lib, path, compound_ids=[self._compound["id"]],
                   on_success=lambda n: self._libraries.infoMessage.emit(f"Exported {n} spectra to {path}."),
                   on_error=self._error_for(key))

    @Slot()
    def copyPeaks(self):
        QGuiApplication.clipboard().setText(peaks_as_text(self._spectrum))

    @Slot(str)
    def copyText(self, text: str):
        QGuiApplication.clipboard().setText(text)
