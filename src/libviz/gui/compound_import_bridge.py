from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from libviz.core import compound_import
from libviz.gui.library_bridge import LibraryBridge, to_local_path
from libviz.gui.worker import start_task

PREVIEW_ROWS = 1000


class CompoundImportBridge(QObject):
    """Library › Import compounds… (ADR 10): file → sheet → column mapping →
    checked preview → import into an open library. Reading the file and
    writing the library run on a worker; re-checking after a mapping change
    is pure Python on rows already in memory."""

    tableChanged = Signal()  # file, sheets, columns, mapping, rows
    busyChanged = Signal()
    errorOccurred = Signal(str)
    imported = Signal(str, str, str)  # library key, summary message, details (skipped/warning rows)

    def __init__(self, libraries: LibraryBridge, parent=None):
        super().__init__(parent)
        self._libraries = libraries
        self._path = ""
        self._sheets: list[str] = []
        self._sheet = ""
        self._header: list[str] = []
        self._table_rows: list[tuple[int, list[str]]] = []
        self._mapping: dict[str, str] = {}
        self._checked_rows: list[compound_import.CompoundRow] = []
        self._error = ""
        self._busy = False

    def _set_busy(self, busy: bool):
        self._busy = busy
        self.busyChanged.emit()

    def _read(self, path: str, sheet: str | None):
        def read():
            sheets = compound_import.sheet_names(path)
            chosen_sheet = sheet if sheet in sheets else (sheets[0] if sheets else "")
            header, table_rows = compound_import.read_table(path, chosen_sheet or None)
            return sheets, chosen_sheet, header, table_rows

        def done(result):
            self._set_busy(False)
            self._sheets, self._sheet, self._header, self._table_rows = result
            self._mapping, self._error = compound_import.guess_mapping(self._header), ""
            self._check()

        def failed(message):
            self._set_busy(False)
            self._header, self._table_rows, self._checked_rows, self._error = [], [], [], message
            self.tableChanged.emit()
        self._path = path
        self._set_busy(True)
        start_task(self, read, on_success=done, on_error=failed)

    def _check(self):
        self._checked_rows = compound_import.check_rows(self._header, self._table_rows, self._mapping)
        self.tableChanged.emit()

    @Slot(str)
    def load(self, url: str):
        self._sheets, self._sheet = [], ""
        self._read(to_local_path(url), None)

    @Slot(str)
    def setSheet(self, sheet: str):
        if sheet != self._sheet and self._path:
            self._read(self._path, sheet)

    @Slot(str, str)
    def setMapping(self, field_key: str, column: str):
        self._mapping[field_key] = column
        self._check()

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=tableChanged)
    def fileName(self) -> str:
        return Path(self._path).name if self._path else ""

    @Property(str, notify=tableChanged)
    def error(self) -> str:
        return self._error

    @Property(list, notify=tableChanged)
    def sheets(self) -> list:
        return self._sheets

    @Property(str, notify=tableChanged)
    def sheet(self) -> str:
        return self._sheet

    @Property(list, notify=tableChanged)
    def columns(self) -> list:
        """Choices for each field's combo box: "" (not used), then the non-empty headers."""
        return [""] + [column for column in self._header if column]

    @Property(list, notify=tableChanged)
    def fields(self) -> list:
        return [{"key": field_key, "label": label, "column": self._mapping.get(field_key, "")}
                for field_key, label in compound_import.FIELDS.items()]

    @Property(list, notify=tableChanged)
    def rows(self) -> list:
        return [{"line": row.line, "name": row.name, "formula": row.formula or "",
                 "mass": "" if row.exact_mass is None else f"{row.exact_mass:.4f}", "inchikey": row.inchikey,
                 "status": row.status, "message": row.error or "; ".join(row.warnings)}
                for row in self._checked_rows[:PREVIEW_ROWS]]

    @Property("QVariantMap", notify=tableChanged)
    def summary(self) -> dict:
        statuses = [row.status for row in self._checked_rows]
        return {"total": len(statuses), "ok": statuses.count("ok"), "warning": statuses.count("warning"),
                "error": statuses.count("error"), "importable": len(statuses) - statuses.count("error")}

    @Slot(str)
    def importInto(self, key: str):
        library = self._libraries.manager.library(key)
        rows = list(self._checked_rows)
        if library is None or self._busy or not rows:
            self.errorOccurred.emit("Choose an open library and a table with compounds.")
            return
        skipped_rows = [row for row in rows if row.status == "error"]
        warning_rows = [row for row in rows if row.status == "warning"]
        details = "\n\n".join(
            f"{title}:\n" + "\n".join(f"line {row.line} {row.name or '(no name)'}: {row.error or '; '.join(row.warnings)}"
                                     for row in section)
            for title, section in (("Skipped", skipped_rows), ("Imported with warnings", warning_rows)) if section)

        def done(counts):
            self._set_busy(False)
            self._libraries.libraryContentChanged.emit(key)
            self._libraries.refresh(key)
            message = (f"Imported compounds into {library.name}: {counts['added']} added, "
                       f"{counts['existing']} already present ({counts['filled']} completed), "
                       f"{len(skipped_rows)} rows skipped, {len(warning_rows)} with warnings.")
            self.imported.emit(key, message, details)

        def failed(message):
            self._set_busy(False)
            self.errorOccurred.emit(message)
        self._set_busy(True)
        start_task(self, compound_import.import_compounds, library, rows, on_success=done, on_error=failed)
