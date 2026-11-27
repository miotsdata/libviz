import re
from dataclasses import replace
from pathlib import Path

import numpy as np
from PySide6.QtCore import Property, QObject, Signal, Slot

from libviz.core import builder
from libviz.core.builder import BuildParams, BuildResult, Group
from libviz.core.readers.mzml_db import db_path_for, eic, profile_ms1_skipped
from libviz.gui.dict_model import DictListModel
from libviz.gui.library_bridge import LibraryBridge, to_local_path
from libviz.gui.worker import start_task

LIBRARY_TARGET_LIMIT = 2000  # compounds listed in "From library…" (filter to narrow)
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
    "storeRt": ("store_rt", bool, bool),
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
    compoundMatchesChanged = Signal()
    libraryCompoundsChanged = Signal()
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
        self._compound_matches: list[dict] = []
        self._match_request = 0  # only the newest search (typing) is shown
        self._library_compounds: list[dict] = []
        self._library_request = 0
        # (m/z, polarity) -> [(file name, rt array, intensity array)], per run.
        self._eics: dict[tuple, list] = {}
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

    @Slot(str, str)
    def addManualTarget(self, formula_or_mz: str, adduct: str):
        """Explore by hand: an m/z or a formula with one adduct, no identity yet."""
        try:
            self._targets.append(builder.manual_target(formula_or_mz, adduct))
        except builder.TargetListError as e:
            self.errorOccurred.emit(str(e))
            return
        self.targetsChanged.emit()

    @Property(list, notify=libraryCompoundsChanged)
    def libraryCompounds(self) -> list:
        return self._library_compounds

    @Slot(str, str)
    def searchLibraryCompounds(self, key: str, text: str):
        """Compounds of library ``key`` to pick as targets (ADR 10), by name,
        InChIKey prefix or formula; all of them (up to the limit) when empty."""
        lib = self._libraries.manager.library(key)
        if lib is None:
            return
        self._library_request += 1
        request = self._library_request

        def found(rows):
            if request == self._library_request:
                self._library_compounds = rows
                self.libraryCompoundsChanged.emit()
        start_task(self, lib.search_compounds, text=text, limit=LIBRARY_TARGET_LIMIT,
                   on_success=found, on_error=self.errorOccurred)

    @Slot(list)
    def addLibraryTargets(self, compounds: list):
        """Library compounds (rows of ``libraryCompounds``) become identified
        targets with the default adducts; commit finds them again by key."""
        known_keys = {t.inchikey for t in self._targets if t.inchikey}
        for compound in compounds:
            if compound["inchikey"] in known_keys or compound.get("exact_mass") is None:
                continue
            self._targets.append(builder.Target(name=compound["name"], formula=compound["formula"],
                                                inchikey=compound["inchikey"], exact_mass=compound["exact_mass"]))
            known_keys.add(compound["inchikey"])
        self.targetsChanged.emit()

    @Slot(int)
    def removeTarget(self, index: int):
        if 0 <= index < len(self._targets):
            del self._targets[index]
            self.targetsChanged.emit()

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
            self.errorOccurred.emit("Load a target list or add a target by hand first.")
            return
        if not self._files:
            self.errorOccurred.emit("Add at least one mzML file.")
            return
        self._set_status(f"Scanning {len(self._files)} file(s)")
        targets, files, params = list(self._targets), list(self._files), self._params

        def done(result):
            self._set_status("")
            self._result = result
            self._eics = {}
            self._selected = -1
            self._rows.set_rows([self._row(i, g) for i, g in enumerate(result.groups)])
            self.resultChanged.emit()
            self.selectGroup(0 if result.groups else -1)
        start_task(self, builder.find_candidates, targets, files, params,
                   on_success=done, on_error=self._fail, on_progress=self._on_progress)

    @Slot()
    def backToSetup(self):
        self._result = None
        self._eics = {}
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
            "rt": "" if g.effective_rt is None else f"{g.effective_rt:.2f}" + (" ✎" if g.rt_set else ""),
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
        if group is not None:
            self._load_eic(group)

    def _load_eic(self, group: Group):
        key = (round(group.target_mz, 5), group.polarity)
        if key in self._eics:
            return
        files, ppm, result = list(self._result.files), self._params.ppm, self._result

        def compute():
            out, profile = [], []
            for f in files:
                db = db_path_for(f)
                rt, intensity = eic(db, group.target_mz, ppm, group.polarity)
                if len(rt):
                    out.append((Path(f).name, rt, intensity))
                elif profile_ms1_skipped(db):
                    profile.append(Path(f).name)
            return out, profile

        def done(series_profile):
            if self._result is result:
                self._eics[key] = series_profile
                self.selectionChanged.emit()
        start_task(self, compute, on_success=done, on_error=self.errorOccurred)

    @Property("QVariantMap", notify=selectionChanged)
    def eic(self) -> dict:
        """The selected row's EIC per file ({key, name, peaks: [[rt, int]]}),
        and its MS2 candidates as sticks at their RT, the chosen one apart."""
        group = self._group()
        cached = self._eics.get((round(group.target_mz, 5), group.polarity)) if group else None
        if cached is None:
            return {}
        series, profile = cached
        note = ("No EIC: MS1 is in profile mode in " + ", ".join(profile)
                + ". Centroid MS1 too (msconvert peakPicking 1-)." if profile else "No MS1 scans with RT in these files.")
        by_file = {name: (rt, intensity) for name, rt, intensity in series}
        groups = [{"key": f"eic{i}", "name": name, "peaks": np.column_stack([rt, y]).tolist()}
                  for i, (name, rt, y) in enumerate(series)]
        scans, chosen, candidates = [], [], []
        for j, c in enumerate(group.candidates):
            if c.rt_min is None or c.file not in by_file:
                continue
            rt, y = by_file[c.file]
            point = [c.rt_min, float(np.interp(c.rt_min, rt, y))]
            (chosen if j == group.chosen else scans).append(point)
            candidates.append({"rt": c.rt_min, "index": j})
        groups.append({"key": "scans", "name": "MS2 scans" if scans else "", "peaks": scans})
        groups.append({"key": "chosen", "name": "Chosen" if chosen else "", "peaks": chosen})
        return {"groups": groups, "candidates": candidates, "note": note}

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

    @Property("QVariantMap", notify=selectionChanged)
    def rowRt(self) -> dict:
        """RT stored with the selected row's spectrum (minutes; "" = none)."""
        group = self._group()
        rt = group.effective_rt if group is not None else None
        return {"text": "" if rt is None else f"{rt:.3f}", "edited": bool(group and group.rt_set)}

    @Slot(int, str)
    def setRt(self, group_index: int, text: str):
        """Set the row's RT by hand; empty text = store no RT."""
        group = self._result.groups[group_index]
        text = text.strip().replace(",", ".")
        try:
            group.rt = float(text) if text else None
        except ValueError:
            self.errorOccurred.emit(f"RT must be a number of minutes, not {text!r}")
            self.selectionChanged.emit()
            return
        group.rt_set = True
        self._changed([group_index])

    @Slot(int)
    def resetRt(self, group_index: int):
        """Back to the chosen scan's RT."""
        group = self._result.groups[group_index]
        group.rt_set, group.rt = False, None
        self._changed([group_index])

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

    @Property(list, notify=resultChanged)
    def manualTargets(self) -> list:
        """Hand-entered targets with a chosen spectrum: identified at commit."""
        r = self._result
        if r is None:
            return []
        chosen = {g.target_index for g in r.groups if g.chosen is not None}
        return [{"index": i, "query": t.query, "identified": t.identified, "name": t.name, "inchikey": t.inchikey,
                 "formula": t.formula}
                for i, t in enumerate(r.targets) if t.query and i in chosen]

    @Property(list, notify=compoundMatchesChanged)
    def compoundMatches(self) -> list:
        return self._compound_matches

    @Slot(str, int, str)
    def findCompounds(self, key: str, target_index: int, text: str):
        """Compounds of library ``key`` to add a hand-entered target to:
        by ``text``, or by the target's mass when ``text`` is empty."""
        lib = self._libraries.manager.library(key)
        if lib is None or self._result is None:
            return
        mass = self._result.targets[target_index].exact_mass
        filters = {"text": text} if text.strip() else {"mass": mass, "ppm": self._params.ppm}
        self._match_request += 1
        request = self._match_request

        def found(rows):
            if request == self._match_request:
                self._compound_matches = rows
                self.compoundMatchesChanged.emit()
        start_task(self, lib.search_compounds, limit=100, **filters, on_success=found, on_error=self.errorOccurred)

    @Slot(int, str, str, str, str)
    def identify(self, target_index: int, name: str, inchikey: str, formula: str, smiles: str):
        try:
            builder.identify(self._result.targets[target_index], name, inchikey, formula, smiles)
        except builder.TargetListError as e:
            self.errorOccurred.emit(str(e))
            return
        self._changed()

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
