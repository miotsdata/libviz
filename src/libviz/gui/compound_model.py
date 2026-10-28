import logging

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Property, Qt, Signal, Slot

from libviz.core.library import Library
from libviz.gui.worker import start_task

logger = logging.getLogger(__name__)

PAGE_SIZE = 200
MAX_PAGES = 50  # ~10k rows cached; scrolling further re-fetches

COLUMNS = [
    ("name", "Name"),
    ("formula", "Formula"),
    ("exact_mass", "Exact mass"),
    ("inchikey", "InChIKey"),
    ("n_spectra", "Spectra"),
]


def _format(key: str, value) -> str:
    if value is None:
        return ""
    if key == "exact_mass":
        return f"{value:.4f}"
    return str(value)


class CompoundTableModel(QAbstractTableModel):
    """The compounds of one library matching the current filters, paged
    (ADR 3).

    ``rowCount`` is the full match count (one COUNT query), so the scrollbar
    is real; rows are fetched ``PAGE_SIZE`` at a time on a worker the first
    time a view asks for them, and shown blank until they arrive. Every
    reset bumps ``_generation`` so pages from a superseded query are dropped.
    """

    countChanged = Signal()
    loadingChanged = Signal()
    sortChanged = Signal()
    errorOccurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lib: Library | None = None
        self._filters: dict = {}
        self._sort = "name"
        self._descending = False
        self._count = 0
        self._pages: dict[int, list[dict]] = {}
        self._pending: set[int] = set()
        self._generation = 0
        self._loading = False

    # --- Qt model API -----------------------------------------------------

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else self._count

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(COLUMNS)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole or not index.isValid():
            return None
        row = self._row(index.row())
        if row is None:
            return ""
        key = COLUMNS[index.column()][0]
        return _format(key, row[key])

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            key, title = COLUMNS[section]
            if key == self._sort:
                title += " ▼" if self._descending else " ▲"
            return title
        return str(section + 1)

    def roleNames(self):
        return {Qt.ItemDataRole.DisplayRole: b"display"}

    # --- paging -------------------------------------------------------------

    def _row(self, row: int) -> dict | None:
        page, offset = divmod(row, PAGE_SIZE)
        rows = self._pages.get(page)
        if rows is None:
            self._request(page)
            return None
        return rows[offset] if offset < len(rows) else None

    def _query(self) -> dict:
        return dict(self._filters, sort=self._sort, descending=self._descending)

    def _request(self, page: int):
        if self._lib is None or page in self._pending:
            return
        self._pending.add(page)
        generation = self._generation
        start_task(self, self._lib.search_compounds, offset=page * PAGE_SIZE, limit=PAGE_SIZE,
                   **self._query(),
                   on_success=lambda rows: self._page_loaded(generation, page, rows),
                   on_error=lambda message: self._failed(generation, message))

    def _page_loaded(self, generation: int, page: int, rows: list[dict]):
        if generation != self._generation:
            return
        self._pending.discard(page)
        self._pages[page] = rows
        while len(self._pages) > MAX_PAGES:
            del self._pages[max(self._pages, key=lambda p: abs(p - page))]
        first = page * PAGE_SIZE
        last = min(first + len(rows), self._count) - 1
        if last >= first:
            self.dataChanged.emit(self.index(first, 0), self.index(last, len(COLUMNS) - 1))

    def _failed(self, generation: int, message: str):
        if generation != self._generation:
            return  # e.g. the library was closed while a page was loading
        self._set_loading(False)
        self.errorOccurred.emit(message)

    def _set_loading(self, value: bool):
        if self._loading != value:
            self._loading = value
            self.loadingChanged.emit()

    def reload(self):
        """Re-run the count + first page for the current library/filters."""
        self._generation += 1
        generation = self._generation
        if self._lib is None:
            self._reset(generation, (0, []))
            return
        lib, query, filters = self._lib, self._query(), dict(self._filters)

        def count_and_first_page():
            return lib.count_compounds(**filters), lib.search_compounds(limit=PAGE_SIZE, **query)

        self._set_loading(True)
        start_task(self, count_and_first_page,
                   on_success=lambda result: self._reset(generation, result),
                   on_error=lambda message: self._failed(generation, message))

    def _reset(self, generation: int, result: tuple[int, list[dict]]):
        if generation != self._generation:
            return
        count, first_page = result
        self.beginResetModel()
        self._count = count
        self._pages = {0: first_page} if count else {}
        self._pending = set()
        self.endResetModel()
        self._set_loading(False)
        self.countChanged.emit()

    # --- API for the bridge / QML --------------------------------------------

    def set_library(self, lib: Library | None):
        """Show ``lib``; filters are cleared (they belong to the old one)."""
        self._lib = lib
        self._filters = {}
        self.reload()

    def set_filters(self, filters: dict):
        self._filters = filters
        self.reload()

    def row_data(self, row: int) -> dict | None:
        return self._row(row) if 0 <= row < self._count else None

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return self._count

    @Property(bool, notify=loadingChanged)
    def loading(self) -> bool:
        return self._loading

    @Property(str, notify=sortChanged)
    def sortKey(self) -> str:
        return self._sort

    @Slot(int, result=bool)
    def isSortable(self, column: int) -> bool:
        return COLUMNS[column][0] in Library.COMPOUND_SORT_KEYS

    @Slot(int)
    def sortByColumn(self, column: int):
        """Header click: sort by that column, or flip the direction."""
        key = COLUMNS[column][0]
        if key not in Library.COMPOUND_SORT_KEYS:
            return
        self._descending = not self._descending if key == self._sort else False
        self._sort = key
        self.sortChanged.emit()
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, len(COLUMNS) - 1)
        self.reload()
