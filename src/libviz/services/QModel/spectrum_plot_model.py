from PySide6.QtCore import QObject, Property, Signal # pylint: disable=no-name-in-module
import numpy as np

class SpectrumPlotModel(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Hardcoded example spectrum
        mz = np.array([50, 75, 100, 125, 150, 200], dtype=np.float32)
        intensity = np.array([10, 40, 100, 60, 20, 80], dtype=np.float32)

        self._set_data(mz, intensity)

    def _set_data(self, mz, intensity):
        if len(intensity) == 0:
            self._peaks = []
            self._min_mz = 0
            self._max_mz = 1
            return

        max_int = intensity.max()
        if max_int > 0:
            norm = (intensity / max_int) * 100
        else:
            norm = intensity

        self._peaks = [
            {"mz": float(m), "intensity": float(i)}
            for m, i in zip(mz, norm)
        ]

        self._min_mz = float(mz.min())
        self._max_mz = float(mz.max())

        self.dataChanged.emit()

    @Property("QVariantList", notify=dataChanged)
    def peaks(self):
        return self._peaks

    @Property(float, notify=dataChanged)
    def minMz(self):
        return self._min_mz

    @Property(float, notify=dataChanged)
    def maxMz(self):
        return self._max_mz
