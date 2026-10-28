# Architecture

```
src/libviz/
  core/    pure Python, no Qt. The library format and all logic.
           MSIAnalyzer imports this, so it is a public API
           (tests/unit/test_public_api.py).
    library.py            Library: one SQLite file (create / load / save / query)
    managers/             LibraryManager: the set of open libraries, keyed by resolved path
    db/                   SQLAlchemy models + alembic migrations (src/libviz/migrations)
    readers/msp_reader.py bulk MSP import
    utils/                MSP parsing, mass/adduct maths, logging
  cli/     command line (no Qt)
  gui/     PySide6 + QML (ADR 2)
    main.py            build_engine() / main(); QML loaded from gui/qml/
    worker.py          Task: the one background-thread runner
    library_bridge.py  `Libraries` context property: open/import/save/close
    inspector_bridge.py `Inspector`: filters, selected compound/spectra/spectrum
    compound_model.py  paged, virtual compound table model (ADR 3)
    qml/Main.qml       window, menubar, sidebar, status bar, dialogs
    qml/Style/         Theme singleton (light/dark tokens)
    qml/Views/         pages and panels
```

## GUI rules

- No DB or file I/O on the GUI thread. Use `start_task(owner, fn, ...)`.
- Bridge and manager state is only mutated in task callbacks, which run on
  the GUI thread.
- Colors come from `Theme`, never hex literals in views.

Layer rules are enforced by `tests/test_architecture.py`: `core` imports
neither `cli` nor `gui`, `cli` doesn't import `gui`, and there are no import
cycles.

## Library lifecycle

- **Temp library:** `Library.load_from_msp` imports into a temp file using
  fast, unsafe pragmas. `is_temp` is True, and `close()` deletes the file.
- **Saved library:** `save_as_db(path)` copies the file atomically (copy,
  then rename), rebinds the engine to `path` with safe pragmas, and drops the
  temp file. See [ADR 1](adr/0001-sqlite-durability-and-temp-libraries.md).

## Decisions

Architecture decision records are in [`docs/adr/`](adr/).
