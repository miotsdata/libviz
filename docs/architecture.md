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
  gui/     PySide6 + QML
```

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
