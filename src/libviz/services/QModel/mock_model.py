# mock_compound_model.py

from PySide6.QtCore import Slot, Qt # pylint: disable=no-name-in-module
from PySide6.QtSql import QSqlQueryModel, QSqlQuery, QSqlDatabase # pylint: disable=no-name-in-module


class MockCompoundModel(QSqlQueryModel):

    CONNECTION_NAME = "MockCompoundConnection"
    DB_PATH = "/Users/matteomiotto/Desktop/metabolomics/LibViz/tests/massbank_neg.db"

    def __init__(self, parent=None):
        super().__init__(parent)

        self._current_filter = ""
        self._current_sort_column = "id"
        self._current_sort_order = "ASC"

        self._init_database()
        self.refresh()

    # ----------------------------
    # Database Initialization
    # ----------------------------

    def _init_database(self):
        """
        Create and open the database connection once.
        """
        print("Starting init")

        if QSqlDatabase.contains(self.CONNECTION_NAME):
            self._db = QSqlDatabase.database(self.CONNECTION_NAME)
        else:
            self._db = QSqlDatabase.addDatabase("QSQLITE", self.CONNECTION_NAME)
            self._db.setDatabaseName(self.DB_PATH)

        if not self._db.open():
            print("Database open failed:", self._db.lastError().text())
        else:
            print("Database opened successfully")

    # ----------------------------
    # Model Refresh
    # ----------------------------

    @Slot()
    def refresh(self):

        if not self._db or not self._db.isOpen():
            print("Database is not open")
            return

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
