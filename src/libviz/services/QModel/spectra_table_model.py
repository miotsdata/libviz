# mock_spectra_model.py

from PySide6.QtCore import Slot # pylint: disable=no-name-in-module
from PySide6.QtSql import QSqlQueryModel, QSqlQuery, QSqlDatabase # pylint: disable=no-name-in-module

class SpectraTableModel(QSqlQueryModel):
    """
    QSqlQueryModel for spectra table.
    Only shows relevant info:
    id, precursor_mz, adduct_type, polarity, collision_energy, added_on
    """

    def __init__(self, library_service, parent=None):
        super().__init__(parent)
        self.library_service = library_service

        self._current_filter_compound_id = None
        self._current_sort_column = "s.id"
        self._current_sort_order = "ASC"
        self._db = None

    # ----------------------------
    # Database Initialization
    # ----------------------------
    def _init_database(self):
        if QSqlDatabase.contains(self.library_service.connection_name):
            self._db = QSqlDatabase.database(self.library_service.connection_name)
        else:
            self._db = QSqlDatabase.addDatabase("QSQLITE", self.library_service.connection_name)
            self._db.setDatabaseName(self.library_service.db_path)

        if not self._db.open():
            print("Database open failed:", self._db.lastError().text())

    # ----------------------------
    # Refresh Model
    # ----------------------------
    @Slot()
    def refresh(self):
        if self._current_filter_compound_id is None:
            self.setQuery("")  # empty
            return

        self._init_database()
        query = QSqlQuery(self._db)

        # Join with adduct_type to get its name
        sql = f"""
            SELECT s.id,
                   s.precursor_mz,
                   at.formula as adduct_type,
                   s.polarity,
                   s.collision_energy,
                   s.added_on,
                   '' as find_button
            FROM spectrum s
            JOIN adduct_type at ON s.adduct_type_id = at.id
            WHERE s.compound_id = ?
            ORDER BY {self._current_sort_column} {self._current_sort_order}
        """

        if not query.prepare(sql):
            print("Prepare failed:", query.lastError().text())
            return

        query.addBindValue(self._current_filter_compound_id)


        if not query.exec():
            print("Query failed:", query.lastError().text())
            return

        self.setQuery(query)

        if self.lastError().isValid():
            print("Model error:", self.lastError().text())

        print("Spectra rows loaded:", self.rowCount())

    # ----------------------------
    # Set filter by compound_id
    # ----------------------------
    @Slot(int)
    def setFilter(self, compound_id: int):
        self._current_filter_compound_id = compound_id
        self.refresh()

    # ----------------------------
    # Sorting
    # ----------------------------
    @Slot(int, str)
    def setSort(self, column_index, order):
        column_map = {
            0: "s.id",
            1: "s.precursor_mz",
            2: "at.formula",
            3: "s.polarity",
            4: "s.collision_energy",
            5: "s.added_on"
        }

        self._current_sort_column = column_map.get(column_index, "s.id")
        self._current_sort_order = "ASC" if order.lower() == "asc" else "DESC"
        self.refresh()

    @Slot(int, result=int)
    def idForRow(self, row: int) -> int:
        """Return the spectra ID at a given row index."""
        record = self.record(row)
        return record.value("id")