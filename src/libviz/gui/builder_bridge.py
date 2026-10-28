import re
from dataclasses import replace
from pathlib import Path

import numpy as np
from PySide6.QtCore import Property, QObject, Signal, Slot

from libviz.core import builder
from libviz.core.builder import BuildParams, BuildResult, Group
from libviz.gui.dict_model import DictListModel
from libviz.gui.library_bridge import LibraryBridge, to_local_path
from libviz.gui.worker import start_task

# QML param name -> (BuildParams field, from-QML conversion, to-QML conversion)
_PARAMS = {
    "ppm": ("ppm", float, float),
    "positiveAdducts": ("positive_adducts", lambda v: tuple(re.split(r"[\s,|]+", str(v).strip())) if str(v).strip() else (), " ".join),
    "negativeAdducts": ("negative_adducts", lambda v: tuple(re.split(r"[\s,|]+", str(v).strip())) if str(v).strip() else (), " ".join),
    "diaMinWidth": ("dia_min_width", float, float),
    "minRelativeIntensity": ("min_relative_intensity", lambda v: float(v) / 100, lambda v: v * 100),
    "removePrecursor": ("remove_precursor", bool, bool),
    "minPeaks": ("min_peaks", int, int),
    "normalize": ("normalize", bool, bool),
    "rankBy": ("rank_by", str, str),
}


def _scaled(c: builder.Candidate | None, sign: float = 1.0) -> list:
    """[[mz, y], ...] with the base peak at ±1000, for the mirror plot."""
    if c is None or not len(c.intensity):
        return []
    y = c.intensity / c.intensity.max() * 1000.0 * sign
    return np.column_stack([c.mz, y]).tolist()


def short_scan_id(scan_id: str) -> str:
    """"controllerType=0 controllerNumber=1 scan=6" -> "scan=6"."""
    return next((part for part in scan_id.split() if part.startswith(("scan=", "index=", "spectrum="))), scan_id)


def group_status(group: Group) -> str:
    if not group.candidates:
        return "missing"
    if group.chosen is None:
        return "rejected"
    return "multiplexed" if group.candidates[group.chosen].multiplexed else "ok"


class BuilderBridge(QObject):
    """GUI side of :mod:`libviz.core.builder`: set up (targets, files,
    parameters), run on a worker, review one row per compound/adduct/CE and
    pick its spectrum, then commit to an open library."""

    targetsChanged = Signal()
    filesChanged = Signal()
    paramsChanged = Signal()
    runningChanged = Signal()
    progressChanged = Signal()
    resultChanged = Signal()  # rows / summary / stage
    selectionChanged = Signal()  # selected group, candidates, preview
    conflictCountChanged = Signal()
    errorOccurred = Signal(str)
    committed = Signal(str, str)  # library key, summary message

    def __init__(self, libraries: LibraryBridge, parent=None):
        super().__init__(parent)
        self._libraries = libraries
        self._targets: list[builder.Target] = []
        self._targets_path = ""
        self._targets_error = ""
        self._files: list[str] = []
        self._params = BuildParams(positive_adducts=("[M+H]+",), negative_adducts=("[M-H]-",))
        self._result: BuildResult | None = None
        self._status = ""
        self._progress = -1.0
        self._selected = -1
        self._preview = -1
        self._conflicts = -1
        self._rows = DictListModel(["index", "target", "formula", "adduct", "polarity", "mz", "ce", "n",
                                    "chosen", "status", "ppm", "rt", "file"], self)

    # --- setup --------------------------------------------------------------

    @Slot(str)
    def loadTargets(self, url: str):
        path = to_local_path(url)

        def loaded(targets):
            self._targets, self._targets_path, self._targets_error = targets, path, ""
            self.targetsChanged.emit()

        def failed(message):
            self._targets, self._targets_path, self._targets_error = [], path, message
            self.targetsChanged.emit()
        start_task(self, builder.parse_targets, path, on_success=loaded, on_error=failed)

    @Property(str, notify=targetsChanged)
    def targetsPath(self) -> str:
        return self._targets_path

    @Property(str, notify=targetsChanged)
    def targetsError(self) -> str:
        return self._targets_error

    @Property(int, notify=targetsChanged)
    def targetCount(self) -> int:
        return len(self._targets)

    @Property(list, notify=targetsChanged)
    def targetsPreview(self) -> list:
        return [{"name": t.name, "formula": t.formula, "adducts": " ".join(t.adducts) or "default",
                 "rt": "" if t.rt_min is None and t.rt_max is None
                 else f"{t.rt_min if t.rt_min is not None else '…'}–{t.rt_max if t.rt_max is not None else '…'}"}
                for t in self._targets[:200]]

    @Slot(list)
    def addFiles(self, urls: list):
        for url in urls:
            path = to_local_path(url)
            if path not in self._files:
                self._files.append(path)
        self.filesChanged.emit()

    @Slot(int)
    def removeFile(self, index: int):
        if 0 <= index < len(self._files):
            del self._files[index]
            self.filesChanged.emit()

    @Slot()
    def clearFiles(self):
        self._files = []
        self.filesChanged.emit()

    @Property(list, notify=filesChanged)
    def files(self) -> list:
        return [{"path": f, "name": Path(f).name} for f in self._files]

    @Property("QVariantMap", notify=paramsChanged)
    def params(self) -> dict:
        return {qml: to_qml(getattr(self._params, field)) for qml, (field, _, to_qml) in _PARAMS.items()}

    @Property(list, constant=True)
    def rankOptions(self) -> list:
        return list(builder.RANK_BY)

    @Slot(str, "QVariant")
    def setParam(self, name: str, value):
        field, from_qml, _ = _PARAMS[name]
        try:
            self._params = replace(self._params, **{field: from_qml(value)})
        except (ValueError, TypeError) as e:
            self.errorOccurred.emit(f"{name}: {e}")
        self.paramsChanged.emit()

    @Property(bool, notify=targetsChanged)
    def canRun(self) -> bool:
        return bool(self._targets)

    # --- run ----------------------------------------------------------------

    @Property(bool, notify=runningChanged)
    def running(self) -> bool:
        return bool(self._status)

    @Property(str, notify=runningChanged)
    def statusText(self) -> str:
        return self._status

    @Property(float, notify=progressChanged)
    def progress(self) -> float:
        return self._progress

    def _set_status(self, status: str):
        self._status = status
        self._progress = -1.0
        self.runningChanged.emit()
        self.progressChanged.emit()

    def _on_progress(self, done: int, total: int):
        self._progress = done / total if total else -1.0
        self.progressChanged.emit()

    def _fail(self, message: str):
        self._set_status("")
        self.errorOccurred.emit(message)

    @Slot()
    def run(self):
        if self.running:
            return
        if not self._targets:
            self.errorOccurred.emit("Load a target list first.")
            return
        if not self._files:
            self.errorOccurred.emit("Add at least one mzML file.")
            return
        self._set_status(f"Scanning {len(self._files)} file(s)")
        targets, files, params = list(self._targets), list(self._files), self._params

        def done(result):
            self._set_status("")
            self._result = result
            self._selected = -1
            self._rows.set_rows([self._row(i, g) for i, g in enumerate(result.groups)])
            self.resultChanged.emit()
            self.selectGroup(0 if result.groups else -1)
        start_task(self, builder.find_candidates, targets, files, params,
                   on_success=done, on_error=self._fail, on_progress=self._on_progress)

    @Slot()
    def backToSetup(self):
        self._result = None
        self._selected = -1
        self._rows.set_rows([])
        self.resultChanged.emit()
        self.selectionChanged.emit()

    # --- review -------------------------------------------------------------

    @Property(str, notify=resultChanged)
    def stage(self) -> str:
        return "review" if self._result is not None else "setup"

    def _row(self, i: int, g: Group) -> dict:
        t = self._result.targets[g.target_index]
        c = g.candidates[g.chosen] if g.chosen is not None else None
        return {
            "index": i, "target": t.name, "formula": t.formula, "adduct": g.adduct, "polarity": g.polarity,
            "mz": g.target_mz, "ce": "" if g.collision_energy is None else f"{g.collision_energy:g}",
            "n": len(g.candidates), "chosen": -1 if g.chosen is None else g.chosen, "status": group_status(g),
            "ppm": "" if c is None or c.ppm_error is None else f"{c.ppm_error:+.1f}",
            "rt": "" if c is None or c.rt_min is None else f"{c.rt_min:.2f}",
            "file": "" if c is None else c.file,
        }

    @Property(QObject, constant=True)
    def rows(self) -> DictListModel:
        return self._rows

    @Property("QVariantMap", notify=resultChanged)
    def summary(self) -> dict:
        r = self._result
        if r is None:
            return {}
        with_spectra = {g.target_index for g in r.groups if g.candidates}
        return {"nTargets": len(r.targets), "nTargetsFound": len(with_spectra), "nGroups": len(r.groups),
                "nChosen": r.n_chosen, "nMs2": r.n_ms2,
                "nMultiplexed": sum(group_status(g) == "multiplexed" for g in r.groups)}

    def _group(self) -> Group | None:
        if self._result is None or not 0 <= self._selected < len(self._result.groups):
            return None
        return self._result.groups[self._selected]

    @Slot(int)
    def selectGroup(self, index: int):
        self._selected = index
        group = self._group()
        self._preview = -1 if group is None or not group.candidates else (
            group.chosen if group.chosen is not None else 0)
        self.selectionChanged.emit()

    @Slot(int)
    def previewCandidate(self, index: int):
        self._preview = index
        self.selectionChanged.emit()

    @Property(int, notify=selectionChanged)
    def selectedGroup(self) -> int:
        return self._selected

    @Property(int, notify=selectionChanged)
    def previewIndex(self) -> int:
        return self._preview

    @Property(list, notify=selectionChanged)
    def candidates(self) -> list:
        group = self._group()
        if group is None:
            return []
        return [{"index": j, "file": c.file, "scanId": short_scan_id(c.scan_id),
                 "rt": "" if c.rt_min is None else f"{c.rt_min:.2f}",
                 "ppm": "DIA" if c.ppm_error is None else f"{c.ppm_error:+.1f}",
                 "intensity": "" if c.precursor_intensity is None else f"{c.precursor_intensity:.3g}",
                 "tic": "" if c.tic is None else f"{c.tic:.3g}",
                 "peaks": c.n_peaks, "multiplexed": c.multiplexed, "chosen": j == group.chosen}
                for j, c in enumerate(group.candidates)]

    @Property("QVariantMap", notify=selectionChanged)
    def preview(self) -> dict:
        """Previewed candidate on top; the chosen one mirrored below when it
        is a different scan (to compare before switching)."""
        group = self._group()
        if group is None or not 0 <= self._preview < len(group.candidates):
            return {}
        target = self._result.targets[group.target_index]
        chosen = group.candidates[group.chosen] if group.chosen not in (None, self._preview) else None
        return {"title": f"{target.name} {group.adduct} CE {self._row(self._selected, group)['ce'] or '—'}",
                "peaks": _scaled(group.candidates[self._preview]),
                "chosenPeaks": _scaled(chosen, -1.0), "isChosen": group.chosen == self._preview}

    def _changed(self, indices=None):
        """Refresh the given rows (all if None) in place, then summary/selection."""
        groups = self._result.groups
        for i in range(len(groups)) if indices is None else indices:
            self._rows.set_row(i, self._row(i, groups[i]))
        self.resultChanged.emit()
        self.selectionChanged.emit()

    @Slot(int, int)
    def choose(self, group_index: int, candidate_index: int):
        """Use candidate ``candidate_index`` for the group; -1: add nothing."""
        group = self._result.groups[group_index]
        group.chosen = candidate_index if 0 <= candidate_index < len(group.candidates) else None
        self._changed([group_index])

    @Slot()
    def chooseBestForAll(self):
        self._result.auto_choose()
        self._changed()

    @Slot()
    def rejectMultiplexed(self):
        for group in self._result.groups:
            if group_status(group) == "multiplexed":
                group.chosen = None
        self._changed()

    # --- commit -------------------------------------------------------------

    @Property(int, notify=conflictCountChanged)
    def conflictCount(self) -> int:
        """Chosen rows the target library already has a spectrum for (-1: unknown)."""
        return self._conflicts

    @Slot(str)
    def countConflicts(self, key: str):
        lib = self._libraries.manager.library(key)
        self._conflicts = -1
        self.conflictCountChanged.emit()
        if lib is None or self._result is None:
            return

        def counted(indices):
            self._conflicts = len(indices)
            self.conflictCountChanged.emit()
        start_task(self, builder.conflicts, lib, self._result, on_success=counted, on_error=self.errorOccurred)

    @Slot(str, bool)
    def commit(self, key: str, replace_existing: bool):
        lib = self._libraries.manager.library(key)
        if lib is None or self._result is None or self.running:
            self.errorOccurred.emit("Choose an open library to add the spectra to.")
            return
        self._set_status(f"Adding {self._result.n_chosen} spectra to {lib.name}")

        def done(counts):
            self._set_status("")
            message = (f"Added {counts['added']}, replaced {counts['replaced']}, "
                       f"skipped {counts['skipped']} existing spectra in {lib.name}.")
            self._libraries.libraryContentChanged.emit(key)
            self._libraries.refresh(key)
            self.committed.emit(key, message)
        start_task(self, builder.commit, lib, self._result, "replace" if replace_existing else "skip",
                   on_success=done, on_error=self._fail)
