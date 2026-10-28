# 2 — GUI architecture: QML from files, bridges, one generic worker

**Status:** Accepted (P1, 2026-10-28)

## Context

The first GUI was a placeholder: a Material-styled window, a compiled
`libviz_resources.py` (qrc) that had to be regenerated after every QML edit,
one bridge with a hand-written `QThread` worker used only for MSP import, and
synchronous DB work on the GUI thread for everything else. MSIAnalyzer has
been through the same problems (its ADRs 15, 50, 51), so this follows what it
settled on, minus what LibViz doesn't need.

## Decision

- **QML is loaded from the package directory** (`gui/qml/`), with no qrc and
  no rcc step. pip installs and PyInstaller bundles ship the files as package
  data. Edits show up on the next launch, and there's no generated file to
  keep in sync.
- **Fusion style + an explicit `palette`** in `Main.qml`. Every role reads
  from the `Style/Theme.qml` singleton, which has the same tokens as
  MSIAnalyzer and a persisted light/dark switch. Material is not used: in
  MSIAnalyzer, Material + the native FileDialog froze the app on GNOME.
- **Desktop layout:** a menubar, a resizable sidebar of open libraries, the
  page for the selected library, and a status bar with a progress bar.
  Recent libraries and the theme are stored with QtCore `Settings`.
- **Bridges are context properties** (`Libraries`, …), parented to the
  engine so QML never outlives them. This fixed a crash on teardown.
- **One worker:** `gui/worker.py`'s `Task` runs `fn(*args)` on a `QThread`
  and emits `succeeded` / `failed` / `progress`. `start_task` connects the
  callbacks *queued*, so plain Python callables run on the GUI thread.
  **No DB or file I/O runs on the GUI thread**, not even `COUNT(*)`.
- **Bridge state stays on the GUI thread.** A task builds or saves a
  `Library` and returns it. The handler then updates `LibraryManager`, so
  the manager's dict is never mutated from a worker thread.
- **One long task at a time** per `LibraryBridge` (`busy`). A second request
  is rejected with a message instead of being queued. That's enough for
  open/import/save; it can be revisited if queueing turns out to be needed.
- **Quit** asks before discarding unsaved (temp) libraries or a running task,
  then `os._exit` (same reason as MSIAnalyzer: a running QThread would block
  interpreter shutdown).

## Consequences

- `tests/gui` uses pytest-qt with `QT_QPA_PLATFORM=offscreen`, and settings
  are isolated to a temp dir. `build_engine()` is the same function
  production uses, so the tests load the real `Main.qml`.
- The `libviz.bridge` package and `libviz.main` are gone. The entry point is
  `libviz-gui` (`libviz.gui.main:main`).
