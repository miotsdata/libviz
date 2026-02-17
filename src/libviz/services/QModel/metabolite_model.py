# mock_compound_model.py

from PySide6.QtCore import Slot, Qt # pylint: disable=no-name-in-module
from PySide6.QtSql import QSqlQueryModel, QSqlQuery, QSqlDatabase # pylint: disable=no-name-in-module
from libviz.services import LibraryService

class CompoundTableModel(QSqlQueryModel):

    def __init__(self, library_service, parent=None):
        super().__init__(parent)

        self.library_service: LibraryService = library_service

        self._current_filter = ""
        self._current_sort_column = "id"
        self._current_sort_order = "ASC"
        self._db = None

    # ----------------------------
    # Database Initialization
    # ----------------------------

    def _init_database(self):
        """
        Create and open the database connection once.
        """
        print("Starting init")

        if QSqlDatabase.contains(self.library_service.connection_name):
            self._db = QSqlDatabase.database(self.library_service.connection_name)
        else:
            self._db = QSqlDatabase.addDatabase("QSQLITE", self.library_service.connection_name)
            self._db.setDatabaseName(self.library_service.db_path)

        if not self._db.open():
            print("Database open failed:", self._db.lastError().text())
        else:
            print("Database opened successfully")

    # ----------------------------
    # Model Refresh
    # ----------------------------

    @Slot()
    def refresh(self):
        print("Refreshing")

        self._init_database()

        query = QSqlQuery(self._db)

        sql = f"""
            SELECT id, name, formula, exact_mass
            FROM compound
            WHERE name LIKE ?
            ORDER BY {self._current_sort_column} {self._current_sort_order}
        """

        if not query.prepare(sql):
            print("Prepare failed:", query.lastError().text())
            return

        query.addBindValue(f"%{self._current_filter}%")

        if not query.exec():
            print("Query failed:", query.lastError().text())
            return

        self.setQuery(query)

        if self.lastError().isValid():
            print("Model error:", self.lastError().text())

        print("Rows loaded:", self.rowCount())

    # ----------------------------
    # Filtering
    # ----------------------------

    @Slot(str)
    def setFilter(self, text):
        self._current_filter = text
        self.refresh()

    # ----------------------------
    # Sorting
    # ----------------------------

    @Slot(int, str)
    def setSort(self, column_index, order):
        column_map = {
            0: "id",
            1: "name",
            2: "formula",
            3: "exact_mass"
        }

        self._current_sort_column = column_map.get(column_index, "id")
        self._current_sort_order = "ASC" if order.lower() == "asc" else "DESC"

        self.refresh()
