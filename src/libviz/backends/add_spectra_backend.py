from PySide6.QtCore import QObject, Slot, Signal # pylint: disable=no-name-in-module

from libviz.services.library_service import LibraryService
from libviz.utils.mass_calulation_utils import calculate_exact_mass_formula_adduct

class AddSpectraBackend(QObject):
    errorOccurred = Signal()

    def __init__(self, library_service: LibraryService):
        super().__init__()
        self.library_service = library_service

    @Slot(str, float, result=float)
    def calculate_mz_from_formula_adduct(self, formula: str, adduct_id: float):
        try:
            if adduct_id == -1:
                delta = 0
            else:
                delta = self.library_service.get_adduct_delta(int(adduct_id))

            return calculate_exact_mass_formula_adduct(formula, delta)
        except Exception as e:
            print("calculate_mz error:", e)
            return float("nan")   # NEVER raise
